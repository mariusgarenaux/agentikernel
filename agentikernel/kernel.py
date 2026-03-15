from pydantic_ai_kernel import PydanticAIBaseKernel

import json
from typing import Annotated

from jupyter_client.blocking.client import BlockingKernelClient
from pydantic_ai import Tool, ModelRetry
from dataclasses import dataclass
import logging


@dataclass
class KernelConnector:
    label: Annotated[str, "The label of the kernel, locally"]
    connection_file: Annotated[str, "The absolute path towards the connection file"]
    agent_tools: Annotated[list[Tool], "The list of agent tools related to this kernel"]
    kernel_client: Annotated[
        BlockingKernelClient, "The client that can access the kernel sockets."
    ]


class AgentiKernel(PydanticAIBaseKernel):

    def __init__(self, **kwargs):
        super().__init__(
            kernel_name="agentikernel",
            authorized_magics_names=[
                "AddKernelMagic",
                "RemoveKernelMagic",
            ],
            **kwargs,
        )
        self.all_kernels_connectors: dict[str, KernelConnector] = {}

        self.user_validation = False
        self.kernel_label_rank = 0
        self.log.setLevel(logging.DEBUG)

    def send_code_to_kernel(self, kernel_label: str, code: str) -> str:
        """
        Executes code on Jupyter Kernel, and returns execution result.

        Parameters:
        ---
            - kernel_label (str): the label of the kernel
            - code (str): the code which will be sent for execution
                to kernel

        Returns :
        ---
            Execution result of the kernel.
        """
        self.log.debug(f"Running code : `{code}` on kernel `{kernel_label}`.")
        if kernel_label not in self.all_kernels_connectors:
            raise KeyError(f"Unknown key {kernel_label} in all_kernels list.")

        client = self.all_kernels_connectors[kernel_label].kernel_client

        self.log.debug(f"Client channels : {client.channels_running}")
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

    def create_tool_read_kernel_history(
        self, kernel_info: dict, kernel_label: str
    ) -> Tool:
        """
        Function that creates a tool for the agent, allowing it to request for kernel
        history.
        This method is not a tool for the agent.

        Parameters :
        ---
            - kernel_info (dict) : the kernel information (from jupyter messaging
                protocol) - language name, version, ...

            - kernel_label (str) : the label given to the kernel, internal to
                agentikernel.
        """
        tool_desc = f"""
        This tools allows you retrieve information from a jupyter kernel.
        You can access to all the code that was executed on the kernel, as well as the output. 

        You can of course propose (if the user asks for it) example of code snippets to answer user's queries.

        Here is the standardized description of the kernel, including what is the language,
        language version, ... :

        {json.dumps(kernel_info['language_info'])}
        """

        tool_label = f"read_history_of_{kernel_label}"
        tool = Tool.from_schema(
            function=lambda: self.read_kernel_history(kernel_label=kernel_label),
            name=tool_label,
            description=tool_desc,
            json_schema={
                "additionalProperties": False,
            },
            takes_ctx=False,
        )
        self.kernel_label_rank += 1
        return tool

    def read_kernel_history(self, kernel_label: str) -> str:
        """
        Read the kernel history, with jupyter messaging protocol.

        Parameters :
        ---
            - kernel_label (str): the (internal) label of the kernel

        Returns :
        ---
            a string containing the formatted history of the kernel.
        """
        self.log.debug(f"Accessing history of kernel `{kernel_label}`.")
        if kernel_label not in self.all_kernels_connectors:
            raise KeyError(f"Unknown key {kernel_label} in all_kernels list.")

        client = self.all_kernels_connectors[kernel_label].kernel_client

        self.log.debug(f"Client channels : {client.channels_running}")

        # Send history request
        msg_id = client.history(
            raw=True,
            output=True,
            hist_access_type="range",
            session=0,
            start=1,
            stop=1000,
        )

        # Wait for reply
        while True:
            msg = client.get_shell_msg()
            if msg["parent_header"].get("msg_id") != msg_id:
                continue

            if msg["msg_type"] == "history_reply":
                # history = msg["content"]["history"]
                self.log.debug(f"Kernel history : {msg['content']}")
                msg_history = msg["content"]["history"]
                break

        string_history = ""
        for session, line, code in msg_history:
            inp, out = code
            string_history += f"In [{line}]: {inp}\n"
            string_history += f"Out[{line}]: {out}\n"

        return string_history

    def create_tool_run_code_on_kernel(
        self, kernel_info: dict, kernel_label: str
    ) -> Tool:
        """
        Creates a pydantic-ai Tool, that can be given to the agent so that
        he can run any code on a kernel.
        """
        tool_desc = f"""
        This tools allows you to send code to a jupyter kernel; and retrieve the execution result.
        The only argument you can give to the tool is the raw_code (string) that needs to be sent
        to the kernel.

        What is inside the code depends on the language of the kernel. For example, it can be python,
        R, octave, ... It can also be just any request in raw text (for example for a kernel that treats
        natural language !)

        Here is the standardized description of the kernel; to help you construct the code you will send
        to this kernel :
        {json.dumps(kernel_info['language_info'])}
        """

        tool_name = f"send_code_to_{kernel_label}"
        tool = Tool.from_schema(
            function=lambda code: self.send_code_to_kernel(
                kernel_label=kernel_label, code=code
            ),
            name=tool_name,
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
        tool.requires_approval = True
        self.kernel_label_rank += 1
        return tool

    def do_shutdown(self, restart):
        for each_kernel in self.all_kernels_connectors:
            self.all_kernels_connectors[each_kernel].kernel_client.stop_channels()
            self.log.debug(f"Stopped channels for kernel {each_kernel}")

        return super().do_shutdown(restart)
