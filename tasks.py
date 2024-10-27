from invoke import task

IMAGE_NAME = "mbround18/k8s-pvc-scaler:latest"


@task
def build(ctx):
    ctx.run(f"docker build -t {IMAGE_NAME} .")


@task
def push(ctx):
    ctx.run(f"docker push {IMAGE_NAME}")


@task
def install_deps(ctx):
    ctx.run("pdm install")


@task
def run_container(ctx):
    ctx.run(f"docker run --rm -it {IMAGE_NAME}")


@task
def clean(ctx):
    print("No clean step defined")
