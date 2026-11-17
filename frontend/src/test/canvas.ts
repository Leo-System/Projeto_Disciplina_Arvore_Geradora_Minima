import { vi } from 'vitest'

// Contexto 2D falso: o jsdom não implementa canvas. Os testes que precisam
// observar o desenho consultam os spies exportados em `context2d`.
export const context2d = {
  setTransform: vi.fn(),
  clearRect: vi.fn(),
  fillText: vi.fn(),
  beginPath: vi.fn(),
  stroke: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  save: vi.fn(),
  translate: vi.fn(),
  rotate: vi.fn(),
  restore: vi.fn(),
  fillRect: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  setLineDash: vi.fn(),
  measureText: vi.fn((texto: string) => ({ width: texto.length * 6 })),
  font: '',
  fillStyle: '',
  strokeStyle: '',
  textAlign: '',
  textBaseline: '',
  lineWidth: 1,
  lineJoin: '',
  lineCap: '',
}

export function limparContexto(): void {
  for (const valor of Object.values(context2d)) {
    if (typeof valor === 'function' && 'mockClear' in valor) valor.mockClear()
  }
}

export function instalarCanvas(): void {
  HTMLCanvasElement.prototype.getContext = vi.fn(
    () => context2d
  ) as unknown as HTMLCanvasElement['getContext']
  HTMLCanvasElement.prototype.getBoundingClientRect = () =>
    ({
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: 800,
      bottom: 520,
      width: 800,
      height: 520,
      toJSON: () => ({}),
    }) as DOMRect
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
    configurable: true,
    get: () => 800,
  })
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
    configurable: true,
    get: () => 520,
  })
  HTMLCanvasElement.prototype.setPointerCapture = () => {}
  HTMLCanvasElement.prototype.releasePointerCapture = () => {}
  HTMLCanvasElement.prototype.hasPointerCapture = () => false
}
