import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import MstEdgeTable from '../components/MstEdgeTable.vue'

const SRC = join(process.cwd(), 'src')

function listarArquivos(diretorio: string): string[] {
  return readdirSync(diretorio).flatMap((nome) => {
    const caminho = join(diretorio, nome)
    if (statSync(caminho).isDirectory()) return listarArquivos(caminho)
    return [caminho]
  })
}

const arquivosVue = listarArquivos(SRC).filter((arquivo) => arquivo.endsWith('.vue'))
const arquivosFonte = listarArquivos(SRC).filter(
  (arquivo) =>
    (arquivo.endsWith('.ts') || arquivo.endsWith('.vue')) && !arquivo.endsWith('.test.ts')
)

function conteudo(arquivo: string): string {
  return readFileSync(arquivo, 'utf8')
}

describe('conformidade e segurança do frontend', () => {
  it('SEC-F-01: não deve usar v-html, innerHTML ou dangerouslySetInnerHTML', () => {
    // Arrange / Act
    const inseguros = arquivosVue.filter((arquivo) =>
      /v-html|innerHTML|dangerouslySetInnerHTML/.test(conteudo(arquivo))
    )

    // Assert
    expect(inseguros).toEqual([])
  })

  it('SEC-F-02: não deve haver console.log no código-fonte', () => {
    // Arrange / Act
    const achados = arquivosFonte.filter((arquivo) => /console\.log\s*\(/.test(conteudo(arquivo)))

    // Assert
    expect(achados).toEqual([])
  })

  it('SEC-F-03: não deve haver segredos fixos no bundle', () => {
    // Arrange
    const padrao = /(api[_-]?key|secret|password|private[_-]?key|bearer\s+[a-z0-9]{8,})/i

    // Act
    const achados = arquivosFonte.filter((arquivo) => padrao.test(conteudo(arquivo)))

    // Assert
    expect(achados).toEqual([])
  })

  it('A11Y-01: não deve haver clique em elementos não interativos', () => {
    // Arrange
    const padrao = /<(div|span|li|p|section|article)[^>]*@click/

    // Act
    const achados = arquivosVue.filter((arquivo) => padrao.test(conteudo(arquivo)))

    // Assert
    expect(achados).toEqual([])
  })

  it('A11Y-02: deve haver abas com role tab e painéis tabpanel', () => {
    // Arrange
    const app = conteudo(join(SRC, 'App.vue'))

    // Act / Assert
    expect(app).toContain('role="tablist"')
    expect(app).toContain('role="tab"')
    expect(app).toContain('role="tabpanel"')
    expect(app).toContain('aria-selected')
  })

  it('A11Y-03: deve exibir legenda textual das cores', () => {
    // Arrange
    const app = conteudo(join(SRC, 'App.vue'))

    // Act / Assert
    expect(app).toContain('Aresta escolhida')
    expect(app).toContain('Aresta do passo atual')
    expect(app).toContain('Ligação manual')
  })

  it('A11Y-04: deve oferecer equivalentes textuais para o canvas', () => {
    // Arrange
    const canvas = conteudo(join(SRC, 'components', 'GraphCanvas.vue'))
    const step = conteudo(join(SRC, 'components', 'StepPlayer.vue'))
    const tabela = conteudo(join(SRC, 'components', 'MstEdgeTable.vue'))

    // Act / Assert
    expect(canvas).toContain('role="img"')
    expect(canvas).toContain('aria-label')
    expect(step).toContain('aria-live')
    expect(tabela).toContain('caption')
  })

  it('C-60: deve renderizar nomes maliciosos como texto, sem HTML', () => {
    // Arrange
    const nomeMalicioso = '<img src=x onerror="alert(1)">'
    const arestas = [{ u: 'A', v: 'B', weight: 1, attrs: { source: 'divisa' } }]

    // Act
    render(MstEdgeTable, {
      props: { edges: arestas, names: { A: nomeMalicioso, B: 'Beta' } },
    })

    // Assert
    expect(screen.getByText(nomeMalicioso)).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
  })
})
