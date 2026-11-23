// No packages to install: the app runs on Python's standard library. This makes a Python 3.11 environment and builds the index.
module.exports = {
  run: [{
    method: "shell.run",
    params: {
      venv: "env",
      venv_python: "3.11",
      message: "python app.py --prepare"
    }
  }, {
    method: "notify",
    params: { html: "Christian Pure Bible Search is installed. Click Start." }
  }]
}
