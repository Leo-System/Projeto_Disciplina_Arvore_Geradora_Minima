import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import UploadPanel from './UploadPanel.vue'

function arquivo(nome = 'rede.csv', conteudo = 'origem,destino,peso\nA,B,1'): File {
  return new File([conteudo], nome, { type: 'text/csv' })
}

async function selecionar(input: HTMLInputElement, file: File): Promise<void> {
  Object.defineProperty(input, 'files', { configurable: true, value: [file] })
  await fireEvent.change(input)
}

describe('UploadPanel', () => {
  it('C-19: deve exibir nome/tamanho do arquivo e habilitar o envio', async () => {
    // Arrange
    const { container } = render(UploadPanel, { props: { loading: false } })
    const input = container.querySelector('input[type="file"]') as HTMLInputElement

    // Act
    await selecionar(input, arquivo('rede.csv', 'a'.repeat(2048)))

    // Assert
    expect(screen.getByText('rede.csv')).toBeInTheDocument()
    expect(screen.getByText('(2 KB)')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Carregar grafo do arquivo' })).toBeEnabled()
  })

  it('C-20: deve aceitar arquivo por arrastar/soltar e limpar o destaque ao sair', async () => {
    // Arrange
    const { container } = render(UploadPanel, { props: { loading: false } })
    const zona = container.querySelector('.drop-zone') as HTMLElement

    // Act: destaque ao arrastar sobre a zona
    await fireEvent.dragOver(zona)
    expect(zona.className).toContain('dragging')

    // Act: saída remove o destaque
    await fireEvent.dragLeave(zona)
    expect(zona.className).not.toContain('dragging')

    // Act: soltar um arquivo
    await fireEvent.drop(zona, { dataTransfer: { files: [arquivo('grafo.json')] } })

    // Assert
    expect(screen.getByText('grafo.json')).toBeInTheDocument()
    expect(zona.className).not.toContain('dragging')
  })

  it('C-21: deve mostrar "Enviando…" e desabilitar o botão durante o envio', () => {
    // Arrange / Act
    render(UploadPanel, { props: { loading: true } })

    // Assert
    const botao = screen.getByRole('button', { name: 'Enviando…' })
    expect(botao).toBeDisabled()
  })

  it('C-22: deve emitir o File selecionado e não emitir sem arquivo', async () => {
    // Arrange
    const { container, emitted } = render(UploadPanel, { props: { loading: false } })
    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    const botao = screen.getByRole('button', { name: 'Carregar grafo do arquivo' })

    // Act: clique sem arquivo não emite
    await fireEvent.click(botao)
    expect(emitted('upload')).toBeUndefined()
    expect(botao).toBeDisabled()

    // Act: seleciona e envia
    const file = arquivo('rede.csv')
    await selecionar(input, file)
    await fireEvent.click(screen.getByRole('button', { name: 'Carregar grafo do arquivo' }))

    // Assert
    const evento = emitted('upload').at(-1) as [File]
    expect(evento[0]).toBe(file)
  })
})
