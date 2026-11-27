const MAX_FILE_SIZE = 2 * 1024 * 1024;

class EnbridgeGasPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  set panel(panel) {
    this._panel = panel;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _render() {
    if (this.shadowRoot.childElementCount) {
      return;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          max-width: 720px;
          margin: 24px auto;
          padding: 0 16px;
          color: var(--primary-text-color);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }
        section {
          padding: 24px;
          border-radius: 12px;
          background: var(--card-background-color, white);
          box-shadow: var(--ha-card-box-shadow, 0 2px 6px #0002);
        }
        h1 { margin-top: 0; }
        input, button { font: inherit; }
        button { margin-top: 16px; padding: 8px 16px; }
        #status { min-height: 1.5em; }
      </style>
      <section>
        <h1>Import Enbridge Gas history</h1>
        <p>Select an Enbridge CSV or XML billing export. The file is processed
        locally by Home Assistant and is not retained.</p>
        <form>
          <input type="file" accept=".csv,.xml,text/csv,application/xml,text/xml"
            required>
          <br>
          <button type="submit">Import usage</button>
        </form>
        <p id="status" role="status" aria-live="polite"></p>
        <p>After import, add <code>enbridge_gas:gas_usage</code> as a gas
        source in the Energy dashboard.</p>
      </section>
    `;

    this.shadowRoot
      .querySelector("form")
      .addEventListener("submit", (event) => this._import(event));
  }

  async _import(event) {
    event.preventDefault();
    const fileInput = this.shadowRoot.querySelector('input[type="file"]');
    const button = this.shadowRoot.querySelector("button");
    const status = this.shadowRoot.querySelector("#status");
    const file = fileInput.files[0];

    if (!file) {
      status.textContent = "Choose a CSV or XML file.";
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      status.textContent = "Files must be 2 MB or smaller.";
      return;
    }
    if (!this._hass || !this._panel?.config?.entry_id) {
      status.textContent = "Home Assistant is not ready. Reload this page.";
      return;
    }

    button.disabled = true;
    status.textContent = "Importing billing history…";
    try {
      const result = await this._hass.callWS({
        type: "enbridge_gas/import",
        entry_id: this._panel.config.entry_id,
        filename: file.name,
        contents: await file.text(),
      });
      status.textContent =
        `Imported ${result.periods} billing periods (${result.total_m3} m³). ` +
        `Added ${result.hours} hourly statistics.`;
      fileInput.value = "";
    } catch (error) {
      status.textContent = error.message || "The export could not be imported.";
    } finally {
      button.disabled = false;
    }
  }
}

customElements.define("enbridge-gas-panel", EnbridgeGasPanel);
