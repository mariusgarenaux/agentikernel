from metakernel import Magic, option
import os
from agentikernel import AgentiKernel, KernelConnector
from jupyter_client.blocking.client import BlockingKernelClient
from pydantic_ai import Tool

ALL_KERNELS_LABELS: list[str] = [
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


class AddKernelMagic(Magic):

    @option(
        "-w",
        "--write",
        action="store_true",
        default=False,
        help="Flag, whether to give rights to the agent to execute code on the kernel. Default to False.",
    )
    @option(
        "-l", "--label", action="store", default=None, help="The label of the kernel"
    )
    def line_add_kernel(
        self,
        path: str,
        write: bool = False,
        label: str | None = None,
    ) -> None:
        """
        Adds the possibility for the agent to interact with the kernel.
        Different modes are proposed :
            - read-only (default) : the agent has a tool that can read the kernel history
                (cell inputs and outputs)
            - read and write : the agent can send code for execution to the kernel, and access
                its history

        Examples :
        ---
            - `%add_kernel ../kernel.json` : adds kernel from connection file located
                at ../kernel.json as a read-only tool (agent can read cell inputs and
                outputs)
            - `%add_kernel ../kernel.json -l py` : same as above, but the label
                of the kernel is set to `py`
            - `%add_kernel ../kernel.json -l py --write` : adds the right to execute
                code on the kernel
        """
        self.kernel: AgentiKernel

        if self.kernel.agent_config is None:
            raise ValueError(
                r"Please load a configuration file for the agent before adding tools. Run %load_config to do so."
            )
        abs_path = os.path.abspath(path)

        if not os.path.isfile(abs_path):
            raise ValueError(f"No file exists at : `{abs_path}`")

        # ensure the kernel is new
        for kernel_connector in self.kernel.all_kernels_connectors.values():
            if kernel_connector.connection_file == abs_path:
                self.kernel.Print(
                    f"A kernel already exists with this connection file : `{kernel_connector.label}`."
                )
                return

        # creates a new kernel connector
        connector_tools: list[Tool] = []
        new_kernel_client: BlockingKernelClient = BlockingKernelClient(
            connection_file=abs_path
        )
        new_kernel_client.load_connection_file()
        self.kernel.log.info(f"Loaded connection file located at {abs_path}")

        new_kernel_client.start_channels()
        kernel_info = None

        msg_id = new_kernel_client.kernel_info()
        self.kernel.log.debug(f"Kernel info message id : `{msg_id}`")
        # Send kernel_info_request
        while True:
            msg = new_kernel_client.get_shell_msg(timeout=5)
            self.kernel.log.debug(f"Message from shell socket : `{msg}`")

            if msg["parent_header"].get("msg_id") != msg_id:
                continue

            msg_type = msg["header"]["msg_type"]

            if msg_type == "kernel_info_reply":
                kernel_info = msg["content"]
                break
            if msg_type == "status":
                if msg["content"]["execution_state"] == "idle":
                    break

        self.kernel.log.debug(f"Retrieved kernel informations : `{kernel_info}`")
        if kernel_info is None:
            self.kernel.log.warning(
                f"Could not retrieve information from kernel connection file {abs_path}"
            )
            return

        if label is None:
            if self.kernel.kernel_label_rank >= len(ALL_KERNELS_LABELS):
                raise Exception("Too much kernel-tools for this agent.")

            label = ALL_KERNELS_LABELS[self.kernel.kernel_label_rank]

        if write:
            self.kernel.log.info("Giving write access to agent towards the kernel !")
            write_tool = self.kernel.create_tool_run_code_on_kernel(kernel_info, label)
            connector_tools.append(write_tool)

        read_tool = self.kernel.create_tool_read_kernel_history(kernel_info, label)
        connector_tools.append(read_tool)

        # adds tools to the kernel
        self.kernel.tools += connector_tools

        try:
            self.kernel.agent = self.kernel.create_agent()  # updates agent
        except ValueError as e:
            new_kernel_client.stop_channels()
            raise ValueError(
                r"Please load a configuration file for the agent before adding tools. Run %load_config to do so."
            ) from e

        self.kernel.all_kernels_connectors[label] = KernelConnector(
            label=label,
            connection_file=abs_path,
            agent_tools=connector_tools,
            kernel_client=new_kernel_client,
        )
        self.kernel.Print(f"Added kernel with label {label} as a tool of the agent.")
        self.kernel.log.info(f"Added kernel {label}.")


def register_magics(kernel) -> None:
    kernel.register_magics(AddKernelMagic)
