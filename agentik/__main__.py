from ipykernel.kernelapp import IPKernelApp
from . import Agentik


IPKernelApp.launch_instance(kernel_class=Agentik)
