from ipykernel.kernelapp import IPKernelApp
from . import AgentiKernel


IPKernelApp.launch_instance(kernel_class=AgentiKernel)
