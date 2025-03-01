import os
import re
import uuid
import asyncio
import tempfile
import aiofiles

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InputData(BaseModel):
    value: str
    type: str


class JacCode(BaseModel):
    code: str
    inputs: list[InputData]


def convert_input(input_data: InputData):
    """Convert input value to the appropriate type."""
    if input_data.type == "int":
        return int(input_data.value)
    elif input_data.type == "float":
        return float(input_data.value)
    elif input_data.type == "str":
        return f'"{input_data.value}"'
    else:
        raise ValueError(f"Unsupported input type: {input_data.type}")


def substitute_inputs(code: str, inputs: list[InputData]) -> str:
    """Replace input() calls with provided values sequentially."""
    input_iter = iter(inputs)

    def replacer(match):
        input_data = next(input_iter)
        return str(convert_input(input_data))

    input_pattern = r"input\s*\(\s*\)"
    return re.sub(input_pattern, replacer, code, count=len(inputs))


async def run_subprocess(command):
    process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    return stdout.decode(), stderr.decode()


@app.post("/run")
async def run_jac_code(jac: JacCode):
    try:
        processed_code = substitute_inputs(jac.code, jac.inputs)

        filename = os.path.join(tempfile.gettempdir(), f"temp_{uuid.uuid4().hex}.jac")
        async with aiofiles.open(filename, "w") as f:
            await f.write(processed_code)

        output, error = await run_subprocess(["jac", "run", filename])

        return {"output": output, "error": error}

    except Exception as e:
        return {"error": str(e)}



@app.get("/debug")
def check_installed_packages():
    import sys
    import subprocess

    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
        return {"installed_packages": result.stdout}
    except Exception as e:
        return {"error": str(e)}
