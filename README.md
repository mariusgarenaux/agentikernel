# Agentikernel

> BETA version

This is an AI agent, wrapped in a jupyter kernel.

It is made to interact with other kernels, through different levels of authorization :

- read kernel history,

(- send code to kernel with user validation) # not yet implemented

- send code to kernel without user validation.

This is a subclass of [pydantic-ai-kernel](https://github.com/mariusgarenaux/pydantic-ai-kernel).

## Getting Started

```bash
pip install agentikernel
```

Then any jupyter front-end could access the kernel, for example :

```bash
pip install jupyter-console
jupyter console --kernel agentikernel
```

for command line interface. But a jupyter notebook would also work.

## Quick start

Create a config file following the scheme [declared here](https://github.com/mariusgarenaux/pydantic-ai-kernel). For example :

```yaml
agent_name: agentik
system_prompt: You are a specialist in code, always ready to analyze code from jupyter kernels.
model:
  model_name: qwen3:1.7b
  model_type: openai
  model_provider:
    name: ollama
    params:
      base_url: http://localhost:11434/v1
```

> a permanent config file can be placed in `~/.jupyter/jupyter_agentikernel_config.yaml`.

Then start the kernel `jupyter console --kernel agentikernel`, and send :

```
%load_config path_to_config_file.yaml
```

The kernel is now initialized with an inference provider.

In an other window, start any jupyter kernel (default is python) :

```bash
jupyter console --ConnectionFileMixin.connection_file ./kernel_connection_file_test.json
```

> It creates a connection file named `kernel_connection_file_test.json`

Within the agentikernel, run :

```
%add_kernel kernel_connection_file_test.json
```

Then, the agentikernel can use the python kernel in read-only mode. It means it can access the cells that have been running on the kernel.

## Commands

All commands from [pydantic-ai-kernel](https://github.com/mariusgarenaux/pydantic-ai-kernel) are inherited (`/load_config`, ...).

We've added the following ones :

- `%add_kernel path_to_kernel_connection_file --label tool_label`

> Declares a tool to the pydantic-ai agent, that allows it to run code on the kernel. The kernel must already be running. The kernel connection file is created when you start any jupyter kernel, see [jupyter_client](https://jupyter-client.readthedocs.io/en/latest/kernels.html#connection-files). They are stored in a runtime directory, that you can access by runnning `jupyter --paths` [ref](https://docs.jupyter.org/en/stable/use/jupyter-directories.html#runtime-files) - see the Runtime paths.

> By default, the agent has read-only access to the kernel. But it can be set to write, by adding the flag: `--write`.

- `%remove_kernel tool_label`

> Removes the connection with the kernel that has label 'tool_label'. And removes the tool to call it for the agent. The kernel is not stopped, we just undeclare it to the agent. Connection can be made again by running %add_kernel.
