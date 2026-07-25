(function () {
  const FIELD_LABELS = JSON.parse(document.getElementById("field-labels").textContent);
  const FIELD_TYPES = JSON.parse(document.getElementById("field-types").textContent);
  const OPERATORS = {
    text: [["contiene", "contiene"], ["igual", "es exactamente"]],
    number: [["mayor_que", "mayor que"], ["menor_que", "menor que"], ["igual", "igual a"]],
    date: [["despues_de", "después de"], ["antes_de", "antes de"], ["en", "en fecha"]],
    bool: [["igual", "es"]],
  };

  const container = document.getElementById("filter-rows");
  const initial = JSON.parse(document.getElementById("initial-filters").textContent);

  function makeRow(field, op, value) {
    const row = document.createElement("div");
    row.className = "filter-row";

    const fieldSelect = document.createElement("select");
    fieldSelect.name = "field";
    Object.entries(FIELD_LABELS).forEach(([key, label]) => {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = label;
      if (key === field) opt.selected = true;
      fieldSelect.appendChild(opt);
    });

    const opSelect = document.createElement("select");
    opSelect.name = "op";

    const valueWrap = document.createElement("div");
    valueWrap.className = "filter-value";

    function renderOperators(type, currentOp) {
      opSelect.innerHTML = "";
      OPERATORS[type].forEach(([key, label]) => {
        const opt = document.createElement("option");
        opt.value = key;
        opt.textContent = label;
        if (key === currentOp) opt.selected = true;
        opSelect.appendChild(opt);
      });
    }

    function renderValueInput(type, currentValue) {
      valueWrap.innerHTML = "";
      let input;
      if (type === "date") {
        input = document.createElement("input");
        input.type = "date";
      } else if (type === "number") {
        input = document.createElement("input");
        input.type = "number";
        input.step = "0.01";
      } else if (type === "bool") {
        input = document.createElement("select");
        ["si", "no"].forEach((v) => {
          const opt = document.createElement("option");
          opt.value = v;
          opt.textContent = v === "si" ? "Sí" : "No";
          input.appendChild(opt);
        });
      } else {
        input = document.createElement("input");
        input.type = "text";
      }
      input.name = "value";
      if (currentValue) input.value = currentValue;
      valueWrap.appendChild(input);
    }

    fieldSelect.addEventListener("change", () => {
      const type = FIELD_TYPES[fieldSelect.value];
      renderOperators(type, null);
      renderValueInput(type, null);
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-remove";
    removeBtn.textContent = "✕";
    removeBtn.addEventListener("click", () => row.remove());

    row.appendChild(fieldSelect);
    row.appendChild(opSelect);
    row.appendChild(valueWrap);
    row.appendChild(removeBtn);
    container.appendChild(row);

    const type = FIELD_TYPES[field] || "text";
    renderOperators(type, op);
    renderValueInput(type, value);
  }

  document.getElementById("add-filter").addEventListener("click", () => {
    makeRow(Object.keys(FIELD_LABELS)[0], null, "");
  });

  if (initial.length) {
    initial.forEach(([field, op, value]) => makeRow(field, op, value));
  } else {
    makeRow(Object.keys(FIELD_LABELS)[0], null, "");
  }
})();
