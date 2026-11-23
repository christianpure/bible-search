const path = require('path')
module.exports = {
  version: "3.7",
  title: "Christian Pure Bible Search",
  description: "Search the Bible and Christian Pure's prayers on your own computer. Type a worry, a question or a verse and get the strongest verses on it and a prayer to pray. Your searches stay on your computer, and it works offline.",
  icon: "icon.png",
  menu: async (kernel, info) => {
    const installed = info.exists("env")
    const running = {
      install: info.running("install.js"),
      start: info.running("start.js"),
      update: info.running("update.js"),
      reset: info.running("reset.js")
    }
    if (running.install) {
      return [{ default: true, icon: "fa-solid fa-plug", text: "Installing", href: "install.js" }]
    }
    if (!installed) {
      return [{ default: true, icon: "fa-solid fa-plug", text: "Install", href: "install.js" }]
    }
    if (running.start) {
      const local = kernel.memory.local[path.resolve(__dirname, "start.js")]
      if (local && local.url) {
        return [
          { default: true, popout: true, icon: "fa-solid fa-book-bible", text: "Open Christian Pure Bible Search", href: local.url },
          { icon: "fa-solid fa-terminal", text: "Terminal", href: "start.js" }
        ]
      }
      return [{ default: true, icon: "fa-solid fa-terminal", text: "Starting", href: "start.js" }]
    }
    if (running.update) return [{ default: true, icon: "fa-solid fa-rotate", text: "Updating", href: "update.js" }]
    if (running.reset) return [{ default: true, icon: "fa-solid fa-broom", text: "Resetting", href: "reset.js" }]
    return [
      { default: true, icon: "fa-solid fa-power-off", text: "Start", href: "start.js" },
      { icon: "fa-solid fa-rotate", text: "Update", href: "update.js" },
      { icon: "fa-solid fa-broom", text: "Reset", href: "reset.js", confirm: "Delete the saved search index and start fresh? Nothing else is removed." }
    ]
  }
}
