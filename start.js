module.exports = async (kernel) => {
  const port = await kernel.port()
  return {
    daemon: true,
    run: [{
      method: "shell.run",
      params: {
        venv: "env",
        env: { PORT: `${port}`, HOST: "127.0.0.1", STUDY_SOURCE: "pinokio" },
        message: "python app.py",
        on: [{ event: "/running at (http:\\/\\/[0-9.:]+)/", done: true }]
      }
    }, {
      method: "local.set",
      params: { url: "{{input.event[1]}}" }
    }]
  }
}
