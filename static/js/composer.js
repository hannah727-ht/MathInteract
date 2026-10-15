
import { api, el, icon } from "/js/common.js";
import { postText } from "/js/math.js";

const MAX_IMAGES = 4;
let counter = 0;

export function createComposer({ label, placeholder = "", text = "", images = [], rows = 5 } = {}) {
  const id = `composer-${++counter}`;
  let attached = [...images];
  let timer = null;

  const textarea = el("textarea", { id, rows, placeholder, class: "composer-text" });
  textarea.value = text;
  const error = el("p", { class: "form-error", role: "alert" });
  const thumbs = el("div", { class: "composer-images" });
  const fileInput = el("input", { type: "file", accept: "image/png,image/jpeg,image/webp", multiple: true, hidden: true });
  const addButton = el("button", { type: "button", class: "btn btn-sm" }, icon("image", "icon icon-sm"), "Add image");
  const previewBox = el("div", { class: "composer-preview-box" });
  const preview = el("div", { class: "composer-preview", hidden: true }, el("span", { class: "composer-preview-label" }, "Preview"), previewBox);

  function updatePreview() {
    const hasMath = /\$|\\\(|\\\[/.test(textarea.value);
    preview.hidden = !hasMath;
    if (hasMath) previewBox.replaceChildren(postText(textarea.value));
  }

  function renderThumbs() {
    thumbs.replaceChildren(
      ...attached.map((img) =>
        el("div", { class: "composer-thumb" },
          el("img", { src: img.url, alt: "Attached image" }),
          el("button", {
            type: "button", class: "thumb-remove", title: "Remove image", "aria-label": "Remove image",
            onclick: () => { attached = attached.filter((a) => a.id !== img.id); renderThumbs(); },
          }, "×")
        )
      )
    );
    addButton.disabled = attached.length >= MAX_IMAGES;
  }

  async function upload(files) {
    error.textContent = "";
    for (const file of files) {
      if (attached.length >= MAX_IMAGES) {
        error.textContent = `A post can have at most ${MAX_IMAGES} images.`;
        break;
      }
      const data = new FormData();
      data.append("file", file);
      addButton.disabled = true;
      addButton.lastChild.textContent = "Uploading…";
      try {
        attached.push(await api("POST", "/api/images", data));
      } catch (e) {
        error.textContent = `${file.name}: ${e.message}`;
      } finally {
        addButton.lastChild.textContent = "Add image";
      }
    }
    renderThumbs();
  }

  textarea.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(updatePreview, 250); });
  addButton.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => { upload([...fileInput.files]); fileInput.value = ""; });

  const element = el("div", { class: "composer" },
    label ? el("label", { for: id, class: "composer-label" }, label) : null,
    textarea,
    el("div", { class: "composer-tools" },
      addButton, fileInput,
      el("span", { class: "hint" }, "Math: $x^2$ in a line, $$x^2$$ on its own line. Up to 4 images (JPG, PNG, WEBP, 5 MB).")
    ),
    thumbs,
    preview,
    error
  );
  renderThumbs();
  updatePreview();

  return {
    element,
    textarea,
    value: () => ({ body: textarea.value, image_ids: attached.map((img) => img.id) }),
    setError: (message) => { error.textContent = message; },
    reset: () => { textarea.value = ""; attached = []; renderThumbs(); updatePreview(); error.textContent = ""; },
  };
}
