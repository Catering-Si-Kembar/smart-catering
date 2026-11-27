import { describe, expect, it } from 'vitest';
import {
  MOCK_MENUS,
  MOCK_ORDERS,
  calculateIngredientsForOrder,
  calculateMinimumDp,
  formatRupiah,
} from './mock-data';

describe('mock-data helpers', () => {
  it('formats rupiah values cleanly and clamps negative numbers to zero', () => {
    expect(formatRupiah(2_500_000)).toBe('Rp 2.500.000');
    expect(formatRupiah(0)).toBe('Rp 0');
    expect(formatRupiah(-500)).toBe('Rp 0');
  });

  it('calculates minimum 60% DP and handles zero or negative inputs', () => {
    expect(calculateMinimumDp(2_500_000)).toBe(1_500_000);
    expect(calculateMinimumDp(1_000_000, 0.5)).toBe(500_000);
    expect(calculateMinimumDp(0)).toBe(0);
    expect(calculateMinimumDp(100_000, 0)).toBe(0);
  });

  it('aggregates ingredients for 100 portions and converts gram->kg and ml->liter', () => {
    const ayamMenu = MOCK_MENUS[0];
    const rows = calculateIngredientsForOrder(ayamMenu, 100);

    expect(rows).toHaveLength(5);
    expect(rows[0]).toMatchObject({
      name: 'Beras Putih',
      totalBaseQuantity: 15_000,
      baseUnit: 'gram',
      formattedShoppingAmount: '15 kg',
    });
    expect(rows[1]).toMatchObject({
      name: 'Ayam Potong',
      totalBaseQuantity: 12_500,
      formattedShoppingAmount: '12,5 kg',
    });
    expect(rows[3]).toMatchObject({
      name: 'Minyak Goreng',
      totalBaseQuantity: 3_000,
      formattedShoppingAmount: '3 liter',
    });
    expect(rows[4]).toMatchObject({
      name: 'Daun Salam',
      totalBaseQuantity: 100,
      formattedShoppingAmount: '100 lembar',
    });
  });

  it('keeps base units when below conversion threshold and handles empty recipes or zero portions', () => {
    const ayamMenu = MOCK_MENUS[0];
    const smallOrder = calculateIngredientsForOrder(ayamMenu, 5);
    expect(smallOrder[0]?.formattedShoppingAmount).toBe('750 gram');
    expect(calculateIngredientsForOrder(ayamMenu, 0)).toEqual([]);

    const noRecipeMenu = MOCK_MENUS.find((item) => item.recipe.length === 0);
    expect(noRecipeMenu).toBeDefined();
    expect(calculateIngredientsForOrder(noRecipeMenu!, 50)).toEqual([]);
  });

  it('marks all mock orders explicitly as synthetic simulation records', () => {
    expect(MOCK_ORDERS.every((order) => order.isSynthetic)).toBe(true);
  });
});
