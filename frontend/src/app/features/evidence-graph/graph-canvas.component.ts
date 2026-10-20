import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  input,
  output,
  signal,
  viewChild,
} from "@angular/core";

import { TranslatePipe } from "../../core/i18n/translate.pipe";
import type { GraphEdge, GraphModel, PositionedNode } from "./evidence-graph.model";
import { layoutGraph } from "./evidence-graph.model";

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Dependency-light SVG renderer for the evidence graph: layered layout
 * (pure `layoutGraph`), viewBox-based zoom/pan/fit, selection with
 * neighbour highlighting and text filtering. Nodes are keyboard
 * focusable; the textual equivalent lives in the page-level tables.
 */
@Component({
  selector: "ds-graph-canvas",
  standalone: true,
  imports: [TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="canvas-wrap">
      <div class="toolbar" role="toolbar" [attr.aria-label]="'graph.toolbar' | t">
        <button type="button" class="ds-btn" (click)="zoomIn()"
                [attr.aria-label]="'graph.zoomIn' | t">+</button>
        <button type="button" class="ds-btn" (click)="zoomOut()"
                [attr.aria-label]="'graph.zoomOut' | t">−</button>
        <button type="button" class="ds-btn" (click)="fit()">
          {{ "graph.fit" | t }}
        </button>
      </div>

      <svg
        #svg
        class="canvas"
        role="img"
        [attr.aria-label]="'graph.canvasLabel' | t"
        tabindex="0"
        [attr.viewBox]="viewBox()"
        (wheel)="onWheel($event)"
        (pointerdown)="onPanStart($event)"
        (pointermove)="onPanMove($event)"
        (pointerup)="onPanEnd()"
        (pointercancel)="onPanEnd()"
        (keydown)="onKeydown($event)"
      >
        <defs>
          <marker
            id="ds-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 9 5 L 0 9 z" class="arrow-head" />
          </marker>
        </defs>

        @for (e of positionedEdges(); track e.edge.id) {
          <g
            class="edge"
            [class.dim]="isDimmedEdge(e.edge)"
            [class.hl]="isHotEdge(e.edge)"
          >
            <path [attr.d]="e.path" marker-end="url(#ds-arrow)" />
            @if (e.labelX !== null) {
              <text class="edge-label" [attr.x]="e.labelX" [attr.y]="e.labelY">
                {{ e.edge.kind }}
              </text>
            }
          </g>
        }

        @for (n of layout().nodes; track n.id) {
          <g
            class="node node--{{ n.kind }} {{ n.accent }}"
            [class.dim]="isDimmedNode(n)"
            [class.selected]="selectedId() === n.id"
            [class.ref-only]="n.referencedOnly"
            [attr.transform]="'translate(' + n.x + ',' + n.y + ')'"
            tabindex="0"
            role="button"
            [attr.aria-label]="nodeLabel(n)"
            [attr.aria-pressed]="selectedId() === n.id"
            (click)="pick(n.id)"
            (keydown.enter)="pick(n.id)"
            (keydown.space)="pick(n.id); $event.preventDefault()"
          >
            <title>{{ n.label }}</title>
            <rect [attr.width]="n.w" [attr.height]="n.h" rx="8" />
            <text class="node-kind" x="12" y="18">{{ n.kind }}</text>
            <text class="node-label" x="12" y="40">{{ clip(n.label) }}</text>
          </g>
        }
      </svg>
    </div>
  `,
  styles: `
    .canvas-wrap {
      position: relative;
      border: 1px solid var(--ds-border);
      border-radius: var(--ds-radius-lg);
      background:
        radial-gradient(
          circle at 1px 1px,
          var(--ds-border-strong) 1px,
          transparent 0
        ),
        var(--ds-surface-1);
      background-size: 24px 24px;
      overflow: hidden;
    }

    .toolbar {
      position: absolute;
      top: var(--ds-space-3);
      right: var(--ds-space-3);
      display: flex;
      gap: var(--ds-space-2);
      z-index: 2;
    }

    .canvas {
      display: block;
      width: 100%;
      height: 460px;
      cursor: grab;
      touch-action: none;
    }

    .canvas:active {
      cursor: grabbing;
    }

    .edge path {
      fill: none;
      stroke: var(--ds-fg-subtle);
      stroke-width: 1.5;
    }

    .edge.hl path {
      stroke: var(--ds-accent);
      stroke-width: 2.5;
    }

    .edge-label {
      fill: var(--ds-fg-subtle);
      font-size: 10px;
      paint-order: stroke;
      stroke: var(--ds-surface-1);
      stroke-width: 3;
      text-anchor: middle;
    }

    .arrow-head {
      fill: var(--ds-fg-subtle);
    }

    .node {
      cursor: pointer;
    }

    .node rect {
      fill: var(--ds-surface-2);
      stroke: var(--ds-border-strong);
      stroke-width: 1.5;
    }

    .node:focus-visible {
      outline: none;
    }

    .node:focus-visible rect {
      stroke: var(--ds-focus-ring);
      stroke-width: 3;
    }

    .node.selected rect {
      stroke: var(--ds-accent);
      stroke-width: 3;
    }

    .node.ref-only rect {
      stroke-dasharray: 4 3;
    }

    .node-kind {
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      fill: var(--ds-fg-subtle);
    }

    .node-label {
      font-size: 11px;
      fill: var(--ds-fg);
    }

    /* kind accents (categorical chart ramp) */
    .node--investigation rect { stroke: var(--ds-accent); }
    .node--investigation .node-kind { fill: var(--ds-accent-strong); }
    .node--evidence rect { stroke: var(--ds-chart-2); }
    .node--evidence .node-kind { fill: var(--ds-chart-2); }
    .node--hypothesis rect { stroke: var(--ds-chart-4); }
    .node--hypothesis .node-kind { fill: var(--ds-chart-4); }
    .node--tool rect { stroke: var(--ds-chart-3); }
    .node--tool .node-kind { fill: var(--ds-chart-3); }
    .node--agent rect { stroke: var(--ds-chart-5); }
    .node--agent .node-kind { fill: var(--ds-chart-5); }

    /* findings carry severity color (real Finding.severity) */
    .node.severity-CRITICAL rect { stroke: var(--ds-severity-critical); }
    .node.severity-CRITICAL .node-kind { fill: var(--ds-severity-critical); }
    .node.severity-HIGH rect { stroke: var(--ds-severity-high); }
    .node.severity-HIGH .node-kind { fill: var(--ds-severity-high); }
    .node.severity-MEDIUM rect { stroke: var(--ds-severity-medium); }
    .node.severity-MEDIUM .node-kind { fill: var(--ds-severity-medium); }
    .node.severity-LOW rect { stroke: var(--ds-severity-low); }
    .node.severity-LOW .node-kind { fill: var(--ds-severity-low); }
    .node.severity-INFO rect { stroke: var(--ds-severity-info); }

    .dim {
      opacity: 0.22;
    }
  `,
})
export class GraphCanvasComponent {
  readonly model = input.required<GraphModel>();
  readonly selectedId = input<string | null>(null);
  /** Free-text filter — non-matching nodes dim (never hidden data). */
  readonly query = input("");
  readonly select = output<string>();

  protected readonly layout = computed(() => layoutGraph(this.model()));
  protected readonly view = signal<ViewBox>({ x: 0, y: 0, w: 100, h: 100 });

  private readonly svgRef =
    viewChild<ElementRef<SVGSVGElement>>("svg");

  private panStart: { px: number; py: number; view: ViewBox } | null = null;

  constructor() {
    // Fit whenever a new graph arrives.
    effect(() => {
      this.layout();
      this.fit();
    });
  }

  protected viewBox(): string {
    const v = this.view();
    return `${v.x} ${v.y} ${v.w} ${v.h}`;
  }

  protected fit(): void {
    const l = this.layout();
    this.view.set({
      x: -16,
      y: -16,
      w: Math.max(l.width + 32, 200),
      h: Math.max(l.height + 32, 160),
    });
  }

  protected zoomIn(): void {
    this.zoomAt(1 / 1.25, null);
  }

  protected zoomOut(): void {
    this.zoomAt(1.25, null);
  }

  protected onWheel(event: WheelEvent): void {
    event.preventDefault();
    const factor = event.deltaY > 0 ? 1.15 : 1 / 1.15;
    this.zoomAt(factor, { px: event.clientX, py: event.clientY });
  }

  private zoomAt(
    factor: number,
    at: { px: number; py: number } | null,
  ): void {
    const svg = this.svgRef()?.nativeElement;
    const rect = svg?.getBoundingClientRect();
    const v = this.view();
    const scale = v.w / Math.max(rect?.width ?? 1, 1);
    const nextW = clamp(v.w * factor, 60, 20000);
    const applied = nextW / v.w;
    const anchorX = at && rect ? v.x + (at.px - rect.left) * scale : v.x + v.w / 2;
    const anchorY = at && rect ? v.y + (at.py - rect.top) * (v.h / Math.max(rect.height, 1)) : v.y + v.h / 2;
    const nextH = v.h * applied;
    this.view.set({
      x: anchorX - (anchorX - v.x) * applied,
      y: anchorY - (anchorY - v.y) * applied,
      w: nextW,
      h: nextH,
    });
  }

  protected onPanStart(event: PointerEvent): void {
    if (event.button !== 0) return;
    const target = event.target as Element;
    if (target.closest(".node")) return; // click selects, drag background pans
    this.panStart = {
      px: event.clientX,
      py: event.clientY,
      view: { ...this.view() },
    };
    (event.currentTarget as Element).setPointerCapture?.(event.pointerId);
  }

  protected onPanMove(event: PointerEvent): void {
    if (!this.panStart) return;
    const svg = this.svgRef()?.nativeElement;
    const rect = svg?.getBoundingClientRect();
    if (!rect || rect.width === 0) return;
    const v0 = this.panStart.view;
    const sx = v0.w / rect.width;
    const sy = v0.h / rect.height;
    this.view.set({
      x: v0.x - (event.clientX - this.panStart.px) * sx,
      y: v0.y - (event.clientY - this.panStart.py) * sy,
      w: v0.w,
      h: v0.h,
    });
  }

  protected onPanEnd(): void {
    this.panStart = null;
  }

  /** Keyboard navigation: arrows pan, +/- zoom, 0 fits. */
  protected onKeydown(event: KeyboardEvent): void {
    const step = this.view().w / 8;
    const v = { ...this.view() };
    switch (event.key) {
      case "ArrowLeft":
        v.x -= step;
        break;
      case "ArrowRight":
        v.x += step;
        break;
      case "ArrowUp":
        v.y -= step;
        break;
      case "ArrowDown":
        v.y += step;
        break;
      case "+":
      case "=":
        this.zoomIn();
        return;
      case "-":
        this.zoomOut();
        return;
      case "0":
        this.fit();
        return;
      default:
        return;
    }
    event.preventDefault();
    this.view.set(v);
  }

  protected pick(id: string): void {
    this.select.emit(id);
  }

  protected clip(label: string): string {
    return label.length > 30 ? `${label.slice(0, 29)}…` : label;
  }

  protected nodeLabel(n: PositionedNode): string {
    return `${n.kind}: ${n.label}`;
  }

  /** Edges resolved to geometry for template rendering. */
  protected positionedEdges = computed(() => {
    const pos = new Map(this.layout().nodes.map((n) => [n.id, n]));
    return this.layout().edges.flatMap((edge) => {
      const a = pos.get(edge.src);
      const b = pos.get(edge.dst);
      if (!a || !b) return [];
      const x1 = a.x + a.w;
      const y1 = a.y + a.h / 2;
      const x2 = b.x;
      const y2 = b.y + b.h / 2;
      const bend = Math.max(48, Math.abs(x2 - x1) / 2);
      return [
        {
          edge,
          path: `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`,
          labelX: (x1 + x2) / 2,
          labelY: (y1 + y2) / 2 - 6,
        },
      ];
    });
  });

  /** 1-hop neighbourhood of the selection, for path highlighting. */
  private readonly neighbourhood = computed<ReadonlySet<string>>(() => {
    const sel = this.selectedId();
    if (!sel) return new Set();
    const keep = new Set<string>([sel]);
    for (const e of this.model().edges) {
      if (e.src === sel) keep.add(e.dst);
      if (e.dst === sel) keep.add(e.src);
    }
    return keep;
  });

  private matchesQuery(n: PositionedNode): boolean {
    const q = this.query().trim().toLowerCase();
    if (!q) return true;
    return (
      n.id.toLowerCase().includes(q) ||
      n.label.toLowerCase().includes(q) ||
      n.kind.includes(q)
    );
  }

  protected isDimmedNode(n: PositionedNode): boolean {
    if (!this.matchesQuery(n)) return true;
    const sel = this.selectedId();
    return !!sel && !this.neighbourhood().has(n.id);
  }

  protected isDimmedEdge(e: GraphEdge): boolean {
    const sel = this.selectedId();
    if (!sel) return false;
    return e.src !== sel && e.dst !== sel;
  }

  protected isHotEdge(e: GraphEdge): boolean {
    const sel = this.selectedId();
    return !!sel && (e.src === sel || e.dst === sel);
  }
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}
