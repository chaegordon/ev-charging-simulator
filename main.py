import io
import matplotlib

matplotlib.use("AGG")
import matplotlib.pyplot as plt
from fastapi import FastAPI, Response, BackgroundTasks

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


# Home page route
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def create_img(name, age):
    plt.rcParams["figure.figsize"] = [7.50, 3.50]
    plt.rcParams["figure.autolayout"] = True
    plt.plot([1, 2])
    plt.title(f"{name} is {age} years old")
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png")
    plt.close()
    return img_buf


# Result page route using path parameters
@app.get("/result/{name}/{age}", response_class=HTMLResponse)
async def get_img(background_tasks: BackgroundTasks, name: str, age: int):
    img_buf = create_img(name, age)
    # get the entire buffer content
    # because of the async, this will await the loading of all content
    bufContents: bytes = img_buf.getvalue()
    background_tasks.add_task(img_buf.close)
    headers = {"Content-Disposition": 'inline; filename="out.png"'}
    return Response(bufContents, headers=headers, media_type="image/png")
