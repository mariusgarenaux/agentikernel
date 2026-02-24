# Agentikernel

An agent wrapped in a jupyter kernel, that can use any kernel as a tool.
This is a subclass of [pydantic-ai-kernel](https://github.com/mariusgarenaux/pydantic-ai-kernel).

We added the '/add_kernel' command that allows to declare to the agent a jupyter kernel as a tool. **The 'tool-kernel' must already be running**, and you just give the agent the path to the kernel connection file.

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
agent_name: pydantic_ai
system_prompt: You are a specialist in cooking, and you are always ready to help people creating new cooking recipees.
model:
  model_name: qwen3:1.7b
  model_type: openai
  model_provider:
    name: ollama
    params:
      base_url: http://localhost:11434/v1
```

Then start the kernel `jupyter console --kernel agentikernel`, and send :

```
/load_config path_to_config_file.yaml
```

The kernel is now initialized with an inference provider.

In an other window, start any jupyter kernel (default is python) :

```bash
jupyter console --ConnectionFileMixin.connection_file ./kernel_connection_file_test.json
```

> It creates a connection file named `kernel_connection_file_test.json`

Within the agentikernel, run :

```
/add_kernel kernel_connection_file_test.json
```

Then, the agentikernel can use the python kernel, and you can access the variables, ... from any jupyter frontend connected to the python kernel.

## Commands

All commands from [pydantic-ai-kernel](https://github.com/mariusgarenaux/pydantic-ai-kernel) are inherited (`/load_config`, ...).

We've added the following ones :

- `/add_kernel path_to_kernel_connection_file --label tool_label`

> Declares a tool to the pydantic-ai agent, that allows it to run code on the kernel. The kernel must already be running. The kernel connection file is created when you start any jupyter kernel, see [jupyter_client](https://jupyter-client.readthedocs.io/en/latest/kernels.html#connection-files). They are stored in a runtime directory, that you can access by runnning `jupyter --paths` [ref](https://docs.jupyter.org/en/stable/use/jupyter-directories.html#runtime-files)

- `/remove_kernel tool_label`

> Removes the connection with the kernel that has label 'tool_label'. And removes the tool to call it for the agent. The kernel is not stopped, we just undeclare it to the agent. Connection can be made again by running /add_kernel.
