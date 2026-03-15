from agentikernel import AgentiKernel
from metakernel import Magic, option


class RemoveKernelMagic(Magic):

    @option(
        "-nf",
        "--not_forget",
        action="store_true",
        default=False,
        help="If set, the agent memory is not empty after the tool removals.",
    )
    def line_remove_kernel(self, label: str, not_forget: bool = False):
        """
        %remove_kernel LABEL : remove all tools related to this kernel
        """
        self.kernel: AgentiKernel  # type hints

        kernel = self.kernel.all_kernels_connectors.get(label, None)
        if kernel is None:
            raise KeyError(f"Could not find any kernel with label `{label}`")

        # stop channel
        kernel.kernel_client.stop_channels()
        self.kernel.log.debug(f"Stopped channel with kernel `{label}`")

        # remove tool from the agent
        tool_names = [tool.name for tool in kernel.agent_tools]
        tool_idx = []
        for k, each_tool in enumerate(self.kernel.tools):
            if each_tool.name in tool_names:
                tool_idx.append(k)

        self.kernel.log.debug(f"Tool indices :  `{tool_idx}`.")

        sorted_indices = sorted(tool_idx, reverse=True)
        for each_tool_idx in sorted_indices:
            if (
                each_tool_idx is not None
                and 0 <= each_tool_idx <= len(self.kernel.tools) - 1
            ):
                self.kernel.log.debug(f"Deleting tool : `{label}`")
                self.kernel.tools.pop(each_tool_idx)

        self.kernel.log.debug(f"List of tools : `{self.kernel.tools}`")

        # deletes the kernel connector
        del self.kernel.all_kernels_connectors[label]

        # re-create the agent with appropriate tools
        self.kernel.agent = self.kernel.create_agent()  # reinitializes agent

        if not not_forget:
            self.kernel.agent_history = []

        self.kernel.Print(f"Removed all tools related to kernel {label}")


def register_magics(kernel) -> None:
    kernel.register_magics(RemoveKernelMagic)
