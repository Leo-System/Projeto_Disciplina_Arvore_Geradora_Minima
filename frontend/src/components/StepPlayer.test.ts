import { fireEvent, render, screen } from '@testing-library/vue'
import { computed, defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import StepPlayer from './StepPlayer.vue'
import { eventosTrace } from '../test/fixtures'
import { buildTraceSnapshot } from '../lib/trace'

const nomes = { A: 'Alfa', B: 'Beta', C: 'Gama', D: 'Delta' }

function montar(indiceInicial = 0, algorithm: 'kruskal' | 'prim' = 'kruskal') {
  const Wrapper = defineComponent({
    setup() {
      const index = ref(indiceInicial)
      const snapshot = computed(() =>
        buildTraceSnapshot(eventosTrace, index.value, nomes, algorithm)
      )
      return () =>
        h(StepPlayer, {
          algorithm,
          events: eventosTrace,
          index: index.value,
          snapshot: snapshot.value,
          'onUpdate:index': (valor: number) => {
            index.value = valor
          },
        })
    },
  })
  return render(Wrapper)
}

describe('StepPlayer', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('C-29: deve operar reiniciar, anterior, reproduzir/pausar, próximo, velocidade e slider', async () => {
    // Arrange
    montar()
    expect(screen.getByText(/Evento 0 de 4/)).toBeInTheDocument()

    // Act: próximo
    await fireEvent.click(screen.getByRole('button', { name: 'Próximo passo' }))
    expect(screen.getByText(/Evento 1 de 4/)).toBeInTheDocument()

    // Act: anterior
    await fireEvent.click(screen.getByRole('button', { name: 'Passo anterior' }))
    expect(screen.getByText(/Evento 0 de 4/)).toBeInTheDocument()

    // Act: slider
    const slider = screen.getByRole('slider', { name: 'Posição na animação' })
    await fireEvent.input(slider, { target: { value: '2' } })
    expect(screen.getByText(/Evento 2 de 4/)).toBeInTheDocument()

    // Act: reproduzir/pausar
    await fireEvent.click(screen.getByRole('button', { name: 'Reproduzir' }))
    expect(screen.getByRole('button', { name: 'Pausar' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Pausar' }))
    expect(screen.getByRole('button', { name: 'Reproduzir' })).toBeInTheDocument()

    // Act: velocidade
    const velocidade = screen.getByRole('combobox', { name: 'Velocidade da animação' })
    await fireEvent.update(velocidade, '1')
    expect(velocidade).toHaveValue('1')

    // Act: reiniciar
    await fireEvent.click(screen.getByRole('button', { name: 'Reiniciar animação' }))
    expect(screen.getByText(/Evento 0 de 4/)).toBeInTheDocument()
  })

  it('C-30: deve desabilitar anterior no início e próximo no fim', () => {
    // Arrange / Act: início
    const { unmount } = render(StepPlayer, {
      props: {
        algorithm: 'kruskal',
        events: eventosTrace,
        index: 0,
        snapshot: buildTraceSnapshot(eventosTrace, 0, nomes, 'kruskal'),
      },
    })

    // Assert
    expect(screen.getByRole('button', { name: 'Passo anterior' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Próximo passo' })).toBeEnabled()
    unmount()

    // Act: fim
    render(StepPlayer, {
      props: {
        algorithm: 'kruskal',
        events: eventosTrace,
        index: eventosTrace.length,
        snapshot: buildTraceSnapshot(eventosTrace, eventosTrace.length, nomes, 'kruskal'),
      },
    })

    // Assert
    expect(screen.getByRole('button', { name: 'Passo anterior' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Próximo passo' })).toBeDisabled()
  })

  it('C-31: deve avançar com fake timers, pausar no fim e limpar o interval no unmount', async () => {
    // Arrange
    vi.useFakeTimers()
    const { unmount } = montar()

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Reproduzir' }))

    // Assert: velocidade padrão 20 => 1 evento a cada 50 ms
    await vi.advanceTimersByTimeAsync(50)
    await nextTick()
    expect(screen.getByText(/Evento 1 de 4/)).toBeInTheDocument()

    await vi.advanceTimersByTimeAsync(50 * eventosTrace.length)
    await nextTick()

    // Assert: pausa automaticamente no fim
    expect(screen.getByText(/Evento 4 de 4/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reproduzir' })).toBeInTheDocument()

    // Act: reinicia a reprodução e desmonta
    await fireEvent.click(screen.getByRole('button', { name: 'Reproduzir' }))
    expect(vi.getTimerCount()).toBe(1)
    unmount()

    // Assert: sem interval vazando
    expect(vi.getTimerCount()).toBe(0)
  })

  it('C-32: deve destacar a linha de pseudocódigo indicada pelo snapshot', () => {
    // Arrange
    const { container } = render(StepPlayer, {
      props: {
        algorithm: 'kruskal',
        events: eventosTrace,
        index: 2,
        snapshot: buildTraceSnapshot(eventosTrace, 2, nomes, 'kruskal'),
      },
    })

    // Act
    const linhas = container.querySelectorAll('.pseudocode li')

    // Assert: evento de aceite do Kruskal => linha 6 (índice 5)
    expect(linhas[5].className).toContain('active')
    expect(linhas[5].textContent).toContain('A ← A ∪')
  })

  it('C-33: deve oferecer explicação aria-live, botões rotulados e slider rotulado', () => {
    // Arrange / Act
    render(StepPlayer, {
      props: {
        algorithm: 'prim',
        events: eventosTrace,
        index: 0,
        snapshot: buildTraceSnapshot(eventosTrace, 0, nomes, 'prim'),
      },
    })

    // Assert
    expect(document.querySelector('[aria-live="polite"]')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reiniciar animação' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Passo anterior' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Próximo passo' })).toBeInTheDocument()
    expect(screen.getByRole('slider', { name: 'Posição na animação' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Velocidade da animação' })).toBeInTheDocument()
  })
})
