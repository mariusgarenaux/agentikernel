from pydantic_ai_kernel import PydanticAIBaseKernel
from pydantic_ai_kernel.kernel import Command
from statikomand import KomandParser
import json

from jupyter_client.blocking.client import BlockingKernelClient
from pydantic_ai import Tool, ModelRetry
from typing import Literal
from dataclasses import dataclass


KernelLabel = Literal[
    "lama",
    "loup",
    "kaki",
    "baba",
    "yack",
    "blob",
    "flan",
    "kiwi",
    "taco",
    "rose",
    "thym",
    "miel",
    "lion",
    "pneu",
    "lune",
    "ciel",
    "coco",
]

ALL_TOOLS_LABELS: list[KernelLabel] = [
    "lama",
    "loup",
    "kaki",
    "baba",
    "yack",
    "blob",
    "flan",
    "kiwi",
    "taco",
    "rose",
    "thym",
    "miel",
    "lion",
    "pneu",
    "lune",
    "ciel",
    "coco",
]


@dataclass
class KernelTool:
    label: KernelLabel
    connection_file: str
    tool: Tool
    kernel_client: BlockingKernelClient


class Agentikernel(PydanticAIBaseKernel):
    def __init__(self, **kwargs):
        super().__init__(kernel_name="agentik", **kwargs)

        add_kernel_parser = KomandParser(prog="add_kernel")
        add_kernel_parser.add_argument(
            "connection_file", completer=self.add_kernel_cmd_completer
        )
        add_kernel_cmd = Command(self.add_kernel_cmd_handler, add_kernel_parser)

        self.all_cmds["/add_kernel"] = add_kernel_cmd

        self.all_kernels: dict[str, KernelTool] = {}
        self.tool_label_rank = 0

    def send_code_to_kernel(self, tool_label: str, code: str) -> str:
        """
        Executes code on Jupyter Kernel, and returns execution result.
        Used as tool for each new kernel added.

        Parameters:
        ---
            - tool_label (str): the label of the kernel
            - code (str): the code which will be sent for execution
                to kernel

        Returns :
        ---
            Execution result of the kernel.
        """
        self.logger.debug(f"Running code : `{code}` on kernel `{tool_label}`.")
        if tool_label not in self.all_kernels:
            raise KeyError(f"Unknown key {tool_label} in all_kernels list.")

        client = self.all_kernels[tool_label].kernel_client

        self.logger.debug(f"Client channels : {client.channels_running}")
        # Start communication channels
        output = None
        # Send execute request
        msg_id = client.execute(code)
        while True:
            msg = client.get_iopub_msg(timeout=5)

            if msg["parent_header"].get("msg_id") != msg_id:
                continue

            msg_type = msg["header"]["msg_type"]

            if msg_type == "stream":
                output = msg["content"]["text"]
                break

            elif msg_type == "execute_result":
                output = msg["content"]["data"].get("text/plain", "")
                break

            elif msg_type == "error":
                raise ModelRetry(f"Error when sending code to kernel : {msg}")

            elif msg_type == "status":
                if msg["content"]["execution_state"] == "idle":
                    break

        if output is None:
            return ""
        return output

    def add_kernel_cmd_completer(self, word: str, rank: int | None) -> list[str]:
        return self.complete_path(word)

    def add_kernel_cmd_handler(self, args):
        """
        Adds a kernel to the tool of the agent. Making possible for the agent
        to run code on this kernel, and retrieve the results.
        """
        if self.agent_config is None:
            raise ValueError(
                "Please load a configuration file for the agent before adding tools. Run /load_config to do so."
            )

        path = args.connection_file

        new_kernel_client = BlockingKernelClient(connection_file=path)
        new_kernel_client.load_connection_file()
        self.logger.info(f"Loaded connection file located at {path}")
        self.all_kernels

        new_kernel_client.start_channels()
        kernel_info = None

        msg_id = new_kernel_client.kernel_info()
        self.logger.debug(f"Kernel info message id : `{msg_id}`")
        # Send kernel_info_request
        while True:
            msg = new_kernel_client.get_shell_msg(timeout=5)
            self.logger.debug(f"Message from shell socket : `{msg}`")

            if msg["parent_header"].get("msg_id") != msg_id:
                continue

            msg_type = msg["header"]["msg_type"]

            if msg_type == "kernel_info_reply":
                kernel_info = msg["content"]
                break
            if msg_type == "status":
                if msg["content"]["execution_state"] == "idle":
                    break

        self.logger.debug(f"Retrieved kernel informations : `{kernel_info}`")
        if kernel_info is None:
            self.logger.warning(
                f"Could not retrieve information from kernel connection file {path}"
            )
            return

        tool_desc = f"""
        This tools allows you to send code to a jupyter kernel; and retrieve the execution result.
        The only argument you can give to the tool is the raw_code (string) that needs to be sent
        to the kernel.

        What is inside the code depends on the language of the kernel. For example, it can be python,
        R, octave, ... It can also be just any request in raw text (for example for a kernel that treats
        natural language !)

        Here is the standardized description of the kernel; to help you construct the code you will send
        to this kernel :
        {json.dumps(kernel_info)}
        """
        if self.tool_label_rank >= len(ALL_TOOLS_LABELS):
            raise Exception("Too much kernel-tools for this agent.")

        tool_label = ALL_TOOLS_LABELS[self.tool_label_rank]
        tool = Tool.from_schema(
            function=lambda code: self.send_code_to_kernel(
                tool_label=tool_label, code=code
            ),
            name=tool_label,
            description=tool_desc,
            json_schema={
                "additionalProperties": False,
                "properties": {
                    "code": {
                        "description": "the code which will be executed on the kernel",
                        "type": "str",
                    },
                },
                "required": ["code"],
                "type": "object",
            },
            takes_ctx=False,
        )
        self.tool_label_rank += 1

        self.tools.append(tool)
        try:
            self.agent = self.create_agent()  # updates agent
        except ValueError as e:
            new_kernel_client.stop_channels()
            raise ValueError(
                "Please load a configuration file for the agent before adding tools. Run /load_config to do so."
            ) from e

        self.all_kernels[tool_label] = KernelTool(
            label=tool_label,
            connection_file=path,
            tool=tool,
            kernel_client=new_kernel_client,
        )
        self.logger.info(
            f"Added tool : {tool_label} to agent. Here is the tool description {tool}"
        )

    def do_shutdown(self, restart):
        for each_kernel in self.all_kernels:
            self.all_kernels[each_kernel].kernel_client.stop_channels()
            self.logger.debug(f"Stopped channels for kernel {each_kernel}")

        return super().do_shutdown(restart)
