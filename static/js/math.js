
import { el } from "/js/common.js";

const DELIMITERS = [
  { left: "$$", right: "$$", display: true },
  { left: "\\[", right: "\\]", display: true },
  { left: "$", right: "$", display: false },
  { left: "\\(", right: "\\)", display: false },
];

export function typeset(node) {
  if (window.renderMathInElement) {
    window.renderMathInElement(node, {
      delimiters: DELIMITERS,
      throwOnError: false,
      ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option"],
    });
  }
}

export function postText(text, className = "post-text") {
  const node = el("div", { class: className }, text);
  typeset(node);
  return node;
}

export function postImages(images) {
  if (!images || !images.length) return null;
  return el("div", { class: "post-images" },
    images.map((img) =>
      el("a", { href: img.url, target: "_blank", rel: "noopener", title: "Open full size" },
        el("img", { src: img.url, alt: "Attached image", loading: "lazy", width: img.width, height: img.height })
      )
    )
  );
}

export function postBody(text, images) {
  return el("div", { class: "post-body" }, postText(text), postImages(images));
}
