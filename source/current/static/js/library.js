document.querySelector("[data-source-filter]")?.addEventListener("input", (event) => {
  const query = event.target.value.trim().normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("pt-BR");
  document.querySelectorAll(".source-row").forEach((row) => {
    const text = row.textContent.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("pt-BR");
    row.hidden = !text.includes(query);
  });
});
