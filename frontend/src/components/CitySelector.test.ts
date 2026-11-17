import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import CitySelector from './CitySelector.vue'
import { cidades } from '../test/fixtures'
import type { City } from '../types'

function muitasCidades(quantidade: number): City[] {
  return Array.from({ length: quantidade }, (_, indice) => ({
    id: `35${String(indice).padStart(5, '0')}`,
    name: `Município ${String(indice).padStart(3, '0')}`,
    lat: -22,
    lon: -49,
    neighbors: [],
  }))
}

describe('CitySelector', () => {
  it('C-13: deve filtrar por nome ignorando acentos/caixa e por código IBGE', async () => {
    // Arrange
    render(CitySelector, { props: { cities: cidades, modelValue: [] } })
    const campo = screen.getByLabelText(/Buscar município por nome ou código IBGE/i)

    // Act: busca sem acento e em minúsculas
    await fireEvent.update(campo, 'sao sebastiao')

    // Assert
    expect(screen.getByText('São Sebastião')).toBeInTheDocument()
    expect(screen.queryByText('Bauru')).not.toBeInTheDocument()

    // Act: busca por código
    await fireEvent.update(campo, '3506003')

    // Assert
    expect(screen.getByText('Bauru')).toBeInTheDocument()
    expect(screen.queryByText('São Sebastião')).not.toBeInTheDocument()
  })

  it('C-14: deve limitar a lista a 160 itens e avisar o usuário', () => {
    // Arrange
    render(CitySelector, { props: { cities: muitasCidades(170), modelValue: [] } })

    // Act
    const itens = screen.getAllByRole('checkbox')
    const aviso = screen.getByText(/Mostrando os 160 primeiros resultados/i)

    // Assert
    expect(itens).toHaveLength(160)
    expect(aviso).toBeInTheDocument()
  })

  it('C-15: deve alternar seleção, refletir chips e remover pelo chip', async () => {
    // Arrange
    const { emitted } = render(CitySelector, {
      props: { cities: cidades, modelValue: ['3506003'] },
    })

    // Assert: chip reflete a seleção atual
    expect(screen.getByRole('button', { name: 'Remover Bauru' })).toBeInTheDocument()

    // Act: adiciona Botucatu pelo checkbox
    await fireEvent.change(screen.getByRole('checkbox', { name: /Botucatu/ }))

    // Assert
    const adicao = emitted('update:modelValue').at(-1) as [string[]]
    expect(adicao[0]).toEqual(['3506003', '3507506'])

    // Act: remove Bauru pelo chip
    await fireEvent.click(screen.getByRole('button', { name: 'Remover Bauru' }))

    // Assert
    const remocao = emitted('update:modelValue').at(-1) as [string[]]
    expect(remocao[0]).toEqual([])
  })

  it('C-16: deve adicionar vizinhos de todos os selecionados sem duplicar', async () => {
    // Arrange
    const { emitted } = render(CitySelector, {
      props: { cities: cidades, modelValue: ['3506003', '3505500'] },
    })

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Adicionar vizinhos' }))

    // Assert: Botucatu entra; São Sebastião (já selecionada) não duplica
    const evento = emitted('update:modelValue').at(-1) as [string[]]
    expect(evento[0].sort()).toEqual(['3505500', '3506003', '3507506'])
    expect(new Set(evento[0]).size).toBe(evento[0].length)
  })

  it('C-17: deve limpar a seleção', async () => {
    // Arrange
    const { emitted } = render(CitySelector, {
      props: { cities: cidades, modelValue: ['3506003', '3505500'] },
    })

    // Act
    await fireEvent.click(screen.getByRole('button', { name: 'Limpar' }))

    // Assert
    const evento = emitted('update:modelValue').at(-1) as [string[]]
    expect(evento[0]).toEqual([])
  })

  it('C-18: deve informar quando nenhum município é encontrado', async () => {
    // Arrange
    render(CitySelector, { props: { cities: cidades, modelValue: [] } })

    // Act
    await fireEvent.update(
      screen.getByLabelText(/Buscar município por nome ou código IBGE/i),
      'cidade-inexistente'
    )

    // Assert
    expect(screen.getByText('Nenhum município encontrado.')).toBeInTheDocument()
  })
})
