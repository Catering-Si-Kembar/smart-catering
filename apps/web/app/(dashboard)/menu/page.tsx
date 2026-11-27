'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import CalculateOutlinedIcon from '@mui/icons-material/CalculateOutlined';
import RestaurantMenuRoundedIcon from '@mui/icons-material/RestaurantMenuRounded';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import { MOCK_MENUS, calculateIngredientsForOrder, formatRupiah } from '@/lib/mock-data';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBanner } from '@/components/ui/status-banner';
import { cn } from '@/lib/utils';

const PORTION_PRESETS = [10, 50, 100] as const;

function MenuCalculatorContent() {
  const searchParams = useSearchParams();
  const initialMenuId = searchParams.get('menuId') ?? MOCK_MENUS[0].id;
  const initialPortions = Number.parseInt(searchParams.get('portions') ?? '100', 10);

  const validInitialMenu = MOCK_MENUS.some((item) => item.id === initialMenuId)
    ? initialMenuId
    : MOCK_MENUS[0].id;
  const validInitialPortions =
    Number.isFinite(initialPortions) && initialPortions > 0 ? initialPortions : 100;

  const [selectedMenuId, setSelectedMenuId] = useState(validInitialMenu);
  const [portions, setPortions] = useState(validInitialPortions);

  const selectedMenu = MOCK_MENUS.find((item) => item.id === selectedMenuId) ?? MOCK_MENUS[0];
  const calculatedRows = calculateIngredientsForOrder(selectedMenu, portions);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-[#21201c] sm:text-2xl">
          Katalog Menu & Kalkulator Bahan Otomatis
        </h1>
        <p className="mt-0.5 text-xs text-[#63635e] sm:text-sm">
          Pilih menu dan jumlah porsi untuk langsung melihat total belanja dapur dengan konversi
          otomatis gram ke kg dan ml ke liter.
        </p>
      </div>

      {/* Kalkulator Bahan Interaktif */}
      <Card className="border-[#dad9d6] bg-white shadow-xs">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <CalculateOutlinedIcon
              sx={{ fontSize: 22 }}
              className="text-[#9e1b32]"
              aria-hidden={true}
            />
            Kalkulator Kebutuhan Bahan Dapur
          </CardTitle>
          <CardDescription className="text-sm text-[#63635e]">
            Uji cepat skenario 10, 50, atau 100 nasi box dalam satu ketukan.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <label htmlFor="calc-menu" className="block text-xs font-semibold text-slate-700">
                Pilih Menu Katering
              </label>
              <select
                id="calc-menu"
                value={selectedMenuId}
                onChange={(event) => setSelectedMenuId(event.target.value)}
                className="min-h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-xs sm:text-sm text-slate-900 focus:border-[#fbcc04] focus:outline-none focus:ring-1 focus:ring-[#fbcc04]"
              >
                {MOCK_MENUS.map((menu) => (
                  <option key={menu.id} value={menu.id}>
                    {menu.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label htmlFor="calc-portions" className="block text-xs font-semibold text-slate-700">
                Jumlah Porsi (Box)
              </label>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  id="calc-portions"
                  type="number"
                  min={1}
                  value={portions}
                  onChange={(event) => {
                    const parsed = Number.parseInt(event.target.value, 10);
                    setPortions(Number.isFinite(parsed) && parsed > 0 ? parsed : 1);
                  }}
                  className="min-h-10 w-24 rounded-lg border border-slate-200 bg-white px-3 text-xs sm:text-sm font-semibold tabular-nums font-mono text-slate-900 focus:border-[#fbcc04] focus:outline-none focus:ring-1 focus:ring-[#fbcc04]"
                />
                {PORTION_PRESETS.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setPortions(preset)}
                    className={cn(
                      'rounded-lg px-2.5 py-1.5 text-xs font-semibold transition shadow-2xs border',
                      portions === preset
                        ? 'bg-[#fbcc04] text-slate-950 border-[#fbcc04]'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
                    )}
                  >
                    {preset} Box
                  </button>
                ))}
              </div>
            </div>
          </div>

          {selectedMenu.recipe.length === 0 ? (
            <StatusBanner
              tone="error"
              title="Resep baku belum tersedia untuk menu ini"
              detail={`Menu "${selectedMenu.name}" belum memiliki takaran resep standar. Lengkapi data resep menu sebelum menghitung kebutuhan belanja.`}
            />
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-amber-50/80 border border-amber-200/60 px-4 py-2.5 text-amber-900">
                <span className="text-xs sm:text-sm font-semibold">
                  Estimasi Belanja untuk {portions} Porsi {selectedMenu.name}
                </span>
                <span className="text-xs sm:text-sm font-bold tabular-nums font-mono">
                  Estimasi Nilai: {formatRupiah(selectedMenu.price * portions)}
                </span>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {calculatedRows.map((row) => (
                  <div
                    key={row.name}
                    className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs"
                  >
                    <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                      {row.name}
                    </p>
                    <p className="mt-1 text-2xl font-bold tabular-nums font-mono tracking-tight text-slate-900">
                      {row.formattedShoppingAmount}
                    </p>
                    <p className="mt-1 text-xs tabular-nums text-slate-400 font-normal">
                      Takaran dasar: {row.totalBaseQuantity.toLocaleString('id-ID')} {row.baseUnit}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Daftar Katalog Menu */}
      <section aria-labelledby="judul-katalog-menu" className="space-y-3">
        <h2 id="judul-katalog-menu" className="text-xl font-bold text-slate-950">
          Daftar Katalog Menu Katering
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          {MOCK_MENUS.map((menu) => (
            <Card
              key={menu.id}
              className="flex flex-col justify-between border-[#dad9d6] bg-white shadow-xs"
            >
              <CardHeader className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Badge
                    variant="secondary"
                    className="border-[#dad9d6] bg-[#f1f0ef] text-xs font-semibold text-[#21201c]"
                  >
                    {menu.category}
                  </Badge>
                  {menu.recipe.length === 0 ? (
                    <Badge
                      variant="outline"
                      className="border-amber-400 bg-amber-50 text-xs font-bold text-amber-950"
                    >
                      <WarningAmberRoundedIcon
                        sx={{ fontSize: 15 }}
                        className="mr-1"
                        aria-hidden={true}
                      />
                      Belum Ada Resep
                    </Badge>
                  ) : null}
                </div>
                <CardTitle className="text-lg font-bold text-[#21201c]">{menu.name}</CardTitle>
                <CardDescription className="text-sm text-[#63635e]">
                  {menu.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-lg font-extrabold tabular-nums text-[#9e1b32]">
                  {formatRupiah(menu.price)}{' '}
                  <span className="text-xs font-normal text-[#82827c]">/ porsi</span>
                </p>
                <Button
                  type="button"
                  variant={selectedMenuId === menu.id ? 'default' : 'secondary'}
                  className="w-full text-xs font-bold gap-1.5"
                  onClick={() => setSelectedMenuId(menu.id)}
                >
                  <RestaurantMenuRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                  <span>Hitung Bahan Menu Ini</span>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

export default function MenuPage() {
  return (
    <Suspense
      fallback={
        <StatusBanner
          tone="loading"
          title="Memuat katalog menu..."
          detail="Menyiapkan daftar paket katering dan kalkulator bahan."
        />
      }
    >
      <MenuCalculatorContent />
    </Suspense>
  );
}
