import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Page } from '@playwright/test'

const RAIZ = resolve(process.cwd(), '..')

function exemplo(nome: string): { name: string; mimeType: string; buffer: Buffer } {
  const caminho = resolve(RAIZ, 'examples', nome)
  return {
    name: nome,
    mimeType: nome.endsWith('.json') ? 'application/json' : 'text/csv',
    buffer: readFileSync(caminho),
  }
}

async function abrirApp(page: Page): Promise<void> {
  await page.route('**/favicon.ico', (rota) => rota.fulfill({ status: 204, body: '' }))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Métricas de Kruskal' })).toBeVisible({
    timeout: 90_000,
  })
}

function cartao(page: Page, rotulo: string) {
  return page.locator('.summary-card', { hasText: rotulo }).locator('strong')
}

async function escolherPreset(page: Page, texto: RegExp): Promise<void> {
  await page.getByRole('button', { name: texto }).click()
}

test.describe('fluxos críticos', () => {
  test('E2E-01: p1 carrega e executa automaticamente sem erro de console', async ({ page }) => {
    // Arrange
    const erros: string[] = []
    page.on('console', (mensagem) => {
      if (mensagem.type() === 'error') erros.push(mensagem.text())
    })
    page.on('pageerror', (erro) => erros.push(erro.message))

    // Act
    await abrirApp(page)

    // Assert
    await expect(
      page.getByRole('heading', { name: 'Bauru e vizinhos diretos', level: 2 })
    ).toBeVisible()
    await expect(page.locator('.stat-chip', { hasText: 'vértices' })).toContainText('8')
    await expect(page.locator('.stat-chip', { hasText: 'arestas' })).toContainText('15')
    await expect(cartao(page, 'Arestas aceitas')).toHaveText('7')
    await expect(page.getByRole('img', { name: /Grafo dos municípios/ })).toBeVisible()
    expect(erros).toEqual([])
  })

  test('E2E-02: p3 com Ambos produz a mesma AGM em Kruskal e Prim', async ({ page }) => {
    // Arrange
    test.setTimeout(180_000)
    await abrirApp(page)

    // Act
    await escolherPreset(page, /Estado de São Paulo \(maior componente\)/)
    await expect(
      page.getByRole('heading', { name: 'Estado de São Paulo (maior componente)', level: 2 })
    ).toBeVisible({ timeout: 120_000 })
    await expect(page.getByRole('heading', { name: 'Métricas de Kruskal' })).toBeVisible({
      timeout: 120_000,
    })

    // Assert: tamanhos da instância
    await expect(page.locator('.stat-chip', { hasText: 'vértices' })).toContainText('644')
    await expect(page.locator('.stat-chip', { hasText: 'arestas' })).toContainText('1.832')
    await expect(cartao(page, 'Arestas aceitas')).toHaveText('643')
    await expect(cartao(page, 'Custo total')).toHaveText(/9\.034,\d{3} km/)

    // Act / Assert: comparação
    await page.getByRole('tab', { name: 'Comparação' }).click()
    await expect(
      page.locator('.comparison-facts div', { hasText: 'Mesmo custo?' }).locator('dd')
    ).toHaveText('Sim')
    await expect(page.locator('.algorithm-card', { hasText: 'Kruskal' })).toContainText(
      '643 arestas'
    )
    await expect(page.locator('.algorithm-card', { hasText: 'Prim' })).toContainText('643 arestas')
  })

  test('E2E-03: selecionar cidades, montar o subgrafo e executar', async ({ page }) => {
    // Arrange
    test.setTimeout(120_000)
    await abrirApp(page)

    // Act
    await page.getByRole('button', { name: 'Selecionar', exact: true }).click()
    await page.getByLabel('Buscar município por nome ou código IBGE').fill('Bauru')
    await page.getByRole('checkbox', { name: /Bauru/ }).check()
    await page.getByRole('button', { name: 'Adicionar vizinhos' }).click()
    await expect(page.getByRole('button', { name: /Montar grafo/ })).toBeEnabled()
    await page.getByRole('button', { name: /Montar grafo/ }).click()

    // Assert
    await expect(
      page.getByRole('heading', { name: /Seleção de \d+ municípios/, level: 2 })
    ).toBeVisible({
      timeout: 90_000,
    })
    await expect(page.getByRole('heading', { name: 'Métricas de Kruskal' })).toBeVisible()
    const vertices = await page.locator('.stat-chip', { hasText: 'vértices' }).innerText()
    expect(Number(vertices.replace(/\D/g, ''))).toBeGreaterThanOrEqual(2)
  })

  test('E2E-04: arquivo inválido mostra erro legível sem quebrar a tela', async ({ page }) => {
    // Arrange
    await abrirApp(page)
    await page.getByRole('button', { name: 'Arquivo', exact: true }).click()
    await page.locator('input[type="file"]').setInputFiles(exemplo('grafo_peso_invalido.csv'))

    // Act
    await page.getByRole('button', { name: 'Carregar grafo do arquivo' }).click()

    // Assert
    const alerta = page.getByRole('alert')
    await expect(alerta).toBeVisible()
    await expect(alerta).toContainText('CSV contém erros de validação')
    await expect(alerta).toContainText("Peso inválido na linha 2: 'abc'")
    await expect(page.getByRole('heading', { name: 'Métricas de Kruskal' })).toBeVisible()
  })

  test('E2E-05: arquivos válidos CSV e JSON carregam e executam', async ({ page }) => {
    // Arrange
    test.setTimeout(120_000)
    await abrirApp(page)
    await page.getByRole('button', { name: 'Arquivo', exact: true }).click()

    // Act: CSV
    await page.locator('input[type="file"]').setInputFiles(exemplo('grafo_valido.csv'))
    await page.getByRole('button', { name: 'Carregar grafo do arquivo' }).click()

    // Assert
    await expect(page.getByRole('heading', { name: 'grafo_valido.csv', level: 2 })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Métricas de Kruskal' })).toBeVisible()
    await expect(cartao(page, 'Custo total')).toHaveText('13,000 km')

    // Act: JSON
    await page.locator('input[type="file"]').setInputFiles(exemplo('grafo_valido.json'))
    await page.getByRole('button', { name: 'Carregar grafo do arquivo' }).click()

    // Assert
    await expect(page.getByRole('heading', { name: 'grafo_valido.json', level: 2 })).toBeVisible()
    await expect(cartao(page, 'Custo total')).toHaveText('86,800 km')
  })

  test('E2E-06: p4 desconexo gera floresta com 18 arestas e 2 componentes', async ({ page }) => {
    // Arrange
    test.setTimeout(120_000)
    await abrirApp(page)

    // Act
    await escolherPreset(page, /Duas regiões separadas/)
    await expect(
      page.getByRole('heading', { name: /Duas regiões separadas/, level: 2 })
    ).toBeVisible({
      timeout: 90_000,
    })

    // Assert
    await expect(page.locator('.stat-chip', { hasText: 'componentes' })).toContainText('2')
    await expect(cartao(page, 'Arestas aceitas')).toHaveText('18')
    await expect(cartao(page, 'Componentes')).toHaveText('2')
    await expect(page.getByText(/floresta geradora mínima/i).first()).toBeVisible()
  })

  test('E2E-07: p5 inclui a ligação manual (balsa) e o filtro de exibição alterna', async ({
    page,
  }) => {
    // Arrange
    test.setTimeout(120_000)
    await abrirApp(page)

    // Act
    await escolherPreset(page, /Litoral norte: Ilhabela/)
    await expect(
      page.getByRole('heading', { name: /Litoral norte: Ilhabela/, level: 2 })
    ).toBeVisible({
      timeout: 90_000,
    })

    // Assert: instância com a ligação manual
    await expect(page.locator('.stat-chip', { hasText: 'vértices' })).toContainText('4')
    await expect(page.locator('.stat-chip', { hasText: 'manual' })).toContainText('1')
    await page.getByRole('tab', { name: 'Resultado' }).click()
    await expect(page.locator('.data-table .badge', { hasText: 'manual' })).toBeVisible()

    // Act: alterna o filtro visual
    const filtro = page.getByLabel('Mostrar ligações manuais')
    await expect(filtro).toBeChecked()
    await filtro.uncheck()
    await expect(filtro).not.toBeChecked()
    await filtro.check()
    await expect(filtro).toBeChecked()
  })

  test('E2E-08: passo a passo reproduz, pausa, avança, volta e atualiza a explicação', async ({
    page,
  }) => {
    // Arrange
    test.setTimeout(120_000)
    await abrirApp(page)
    await page.getByRole('tab', { name: /Passo a passo/ }).click()
    await expect(page.getByRole('heading', { name: /Passo a passo — Kruskal/ })).toBeVisible()

    const explicacao = page.locator('.step-explanation')
    const textoInicial = await explicacao.innerText()
    expect(await page.locator('.step-explanation').getAttribute('aria-live')).toBe('polite')

    // Act: próximo
    await page.getByRole('button', { name: 'Próximo passo' }).click()
    await expect(page.getByText(/Evento 1 de/)).toBeVisible()
    expect(await explicacao.innerText()).not.toBe(textoInicial)

    // Assert: pseudocódigo com linha ativa
    await expect(page.locator('.pseudocode li.active')).toHaveCount(1)

    // Act: reproduzir e pausar
    await page.getByRole('button', { name: 'Reproduzir' }).click()
    await expect(page.getByText(/Evento ([2-9]|\d{2,}) de/)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: 'Pausar' }).click()

    // Act: anterior e reiniciar
    await page.getByRole('button', { name: 'Passo anterior' }).click()
    await page.getByRole('button', { name: 'Reiniciar animação' }).click()
    await expect(page.getByText(/Evento 0 de/)).toBeVisible()
  })

  test('E2E-09: benchmark exibe tabela/gráfico e sinaliza reexecução', async ({ page }) => {
    // Arrange
    test.setTimeout(180_000)
    await abrirApp(page)
    await page.getByRole('tab', { name: 'Benchmark' }).click()
    await expect(page.getByText('Nenhuma medição ainda')).toBeVisible()

    // Act
    await page.getByLabel('Execuções por tamanho').fill('1')
    await page.getByRole('button', { name: 'Executar benchmark' }).click()

    // Assert
    await expect(page.locator('.benchmark-chart')).toBeVisible({ timeout: 120_000 })
    await expect(page.locator('.benchmark-table tbody tr')).toHaveCount(7)
    await expect(page.getByRole('img', { name: /Gráfico de linhas/ })).toBeVisible()

    // Act: reexecuta com mais execuções para observar o loading
    await page.getByLabel('Execuções por tamanho').fill('5')
    await page.getByRole('button', { name: 'Executar benchmark' }).click()

    // Assert: estado de carregamento visível (botão "Medindo…")
    await expect(page.getByRole('button', { name: 'Medindo…' })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Executar benchmark' })).toBeEnabled({
      timeout: 120_000,
    })
  })

  test('E2E-10: abas Teoria e Modelagem exibem conceitos e limitações', async ({ page }) => {
    // Arrange
    await abrirApp(page)

    // Act
    await page.getByRole('tab', { name: 'Teoria' }).click()

    // Assert
    const teoria = await page.locator('#panel-teoria').innerText()
    for (const termo of [
      'árvore geradora',
      'n − 1',
      'Propriedade do corte',
      'Propriedade do ciclo',
      'Kruskal',
      'Union-Find',
      'Prim',
      'heap',
      'esparsos',
      'densos',
      'caminho mais curto',
    ]) {
      expect(teoria).toContain(termo)
    }

    // Act
    await page.getByRole('tab', { name: 'Modelagem' }).click()

    // Assert
    await expect(page.getByRole('heading', { name: 'Hipóteses e limitações' })).toBeVisible()
    await expect(page.locator('#panel-modelagem .limitations-list > li')).toHaveCount(6)
  })

  test('E2E-12: uso do sistema não faz requisições externas', async ({ page }) => {
    // Arrange
    const externas: string[] = []
    const origem = 'http://127.0.0.1:8123'
    page.on('request', (requisicao) => {
      const url = requisicao.url()
      if (!url.startsWith(origem) && !url.startsWith('data:') && !url.startsWith('blob:')) {
        externas.push(url)
      }
    })

    // Act
    await abrirApp(page)
    for (const aba of ['Resultado', 'Comparação', 'Passo a passo', 'Teoria', 'Modelagem']) {
      await page.getByRole('tab', { name: new RegExp(aba) }).click()
    }

    // Assert
    expect(externas).toEqual([])
  })
})

test.describe('acessibilidade e responsividade', () => {
  test('E2E-11: fluxo principal por teclado e layout em 360px sem overflow', async ({ page }) => {
    // Arrange
    test.setTimeout(120_000)
    await page.setViewportSize({ width: 360, height: 800 })
    await abrirApp(page)

    // Assert: sem rolagem horizontal
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    )
    expect(overflow).toBeLessThanOrEqual(1)

    // Act: navega por Tab até o botão de execução
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur())
    let encontrou = false
    for (let indice = 0; indice < 250; indice += 1) {
      await page.keyboard.press('Tab')
      const texto = await page.evaluate(
        () => (document.activeElement as HTMLElement | null)?.textContent ?? ''
      )
      if (texto.includes('Executar algoritmos')) {
        encontrou = true
        break
      }
    }
    expect(encontrou).toBe(true)

    // Act: aciona pelo teclado e observa a requisição real
    const resposta = page.waitForResponse(
      (r) => r.url().endsWith('/api/v1/run') && r.request().method() === 'POST'
    )
    await page.keyboard.press('Enter')
    expect((await resposta).ok()).toBe(true)
    await expect(page.getByRole('button', { name: 'Executar algoritmos' })).toBeEnabled({
      timeout: 90_000,
    })
  })
})
