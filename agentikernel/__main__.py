from ipykernel.kernelapp import IPKernelApp
from . import Agentikernel


IPKernelApp.launch_instance(kernel_class=Agentikernel)
