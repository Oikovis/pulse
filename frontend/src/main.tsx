import { StrictMode, createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MotionConfig } from "framer-motion";

import { App } from "./App";
import tailwindCss from "./design/tailwind.css?inline";
import { IS_DEMO, getDemoHass } from "./lib/env";
import type { HassObject, PanelInfo, PanelRoute } from "./hass/types";

const sheet = new CSSStyleSheet();
sheet.replaceSync(tailwindCss);

const HassContext = createContext<HassObject | undefined>(undefined);

export function useHass(): HassObject | undefined {
  return useContext(HassContext);
}

function PanelRoot({ host }: { host: OikovisPulsePanel }) {
  const [hass, setHass] = useState<HassObject | undefined>(host.hass ?? (IS_DEMO ? getDemoHass() : undefined));

  useEffect(() => {
    const sub = (next: HassObject | undefined) => setHass(next);
    host.subscribe(sub);
    return () => host.unsubscribe(sub);
  }, [host]);

  return (
    <HassContext.Provider value={hass}>
      <MotionConfig reducedMotion="user">
        <Wrapper>
          <App />
        </Wrapper>
      </MotionConfig>
    </HassContext.Provider>
  );
}

function Wrapper({ children }: { children: ReactNode }) {
  return <div className="oikovis-pulse-root h-full w-full">{children}</div>;
}

type HassSubscriber = (hass: HassObject | undefined) => void;

class OikovisPulsePanel extends HTMLElement {
  private _hass: HassObject | undefined;
  private _root: Root | undefined;
  private _mount: HTMLDivElement | undefined;
  private _subs = new Set<HassSubscriber>();

  // HA-injected properties (we don't act on these yet, but record them for future use)
  public narrow?: boolean;
  public route?: PanelRoute;
  public panel?: PanelInfo;

  constructor() {
    super();
    const shadow = this.attachShadow({ mode: "open" });
    shadow.adoptedStyleSheets = [sheet];

    const mount = document.createElement("div");
    mount.style.height = "100%";
    mount.style.width = "100%";
    shadow.appendChild(mount);
    this._mount = mount;
  }

  connectedCallback() {
    if (!this._mount || this._root) return;
    this._root = createRoot(this._mount);
    this._root.render(
      <StrictMode>
        <PanelRoot host={this} />
      </StrictMode>,
    );
  }

  disconnectedCallback() {
    this._root?.unmount();
    this._root = undefined;
  }

  set hass(value: HassObject | undefined) {
    this._hass = value;
    for (const sub of this._subs) sub(value);
  }

  get hass(): HassObject | undefined {
    return this._hass;
  }

  subscribe(fn: HassSubscriber): void {
    this._subs.add(fn);
  }

  unsubscribe(fn: HassSubscriber): void {
    this._subs.delete(fn);
  }
}

if (!customElements.get("oikovis-pulse-panel")) {
  customElements.define("oikovis-pulse-panel", OikovisPulsePanel);
}
