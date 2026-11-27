export type OrderStatus =
  'DRAFT' | 'CONFIRMED' | 'IN_PREPARATION' | 'READY' | 'DELIVERED' | 'CANCELLED';

export type PaymentStatus = 'UNPAID' | 'PARTIALLY_PAID' | 'PAID';

export interface MockRecipeIngredient {
  readonly name: string;
  readonly quantityPerPortion: number;
  readonly baseUnit: 'gram' | 'ml' | 'butir' | 'lembar';
  readonly shoppingUnit?: 'kg' | 'liter';
  readonly conversionFactor?: number;
}

export interface MockMenuItem {
  readonly id: string;
  readonly name: string;
  readonly category: 'Nasi Box' | 'Prasmanan' | 'Snack Box';
  readonly price: number;
  readonly description: string;
  readonly recipe: readonly MockRecipeIngredient[];
}

export interface MockOrder {
  readonly id: string;
  readonly orderNumber: string;
  readonly customerAlias: string;
  readonly eventDate: string;
  readonly eventTime: string;
  readonly menuId: string;
  readonly menuName: string;
  readonly portions: number;
  readonly totalAmount: number;
  readonly status: OrderStatus;
  readonly paymentStatus: PaymentStatus;
  readonly paidAmount: number;
  readonly deliveryArea: string;
  readonly notes: string;
  readonly isSynthetic: true;
}

export interface MockNotification {
  readonly id: string;
  readonly title: string;
  readonly message: string;
  readonly timeLabel: string;
  readonly category: 'JADWAL' | 'KEUANGAN' | 'BAHAN';
  readonly adminOnly: boolean;
  readonly isRead: boolean;
}

export interface CalculatedIngredientRow {
  readonly name: string;
  readonly totalBaseQuantity: number;
  readonly baseUnit: string;
  readonly formattedShoppingAmount: string;
}

export const MIN_DP_RATIO = 0.6;

export const ORDER_STATUS_META: Record<
  OrderStatus,
  { readonly label: string; readonly tone: 'neutral' | 'info' | 'warning' | 'success' | 'danger' }
> = {
  DRAFT: { label: 'Menunggu DP', tone: 'warning' },
  CONFIRMED: { label: 'Pesanan Dikonfirmasi', tone: 'info' },
  IN_PREPARATION: { label: 'Sedang Dimasak di Dapur', tone: 'warning' },
  READY: { label: 'Matang · Siap Diantar', tone: 'success' },
  DELIVERED: { label: 'Selesai Terkirim', tone: 'neutral' },
  CANCELLED: { label: 'Dibatalkan', tone: 'danger' },
};

export const PAYMENT_STATUS_META: Record<
  PaymentStatus,
  { readonly label: string; readonly tone: 'warning' | 'info' | 'success' | 'danger' }
> = {
  UNPAID: { label: 'Belum Bayar DP', tone: 'danger' },
  PARTIALLY_PAID: { label: 'Sudah Bayar DP 60%', tone: 'warning' },
  PAID: { label: 'Lunas 100%', tone: 'success' },
};

export const MOCK_MENUS: readonly [MockMenuItem, ...MockMenuItem[]] = [
  {
    id: 'menu-ayam-lengkuas',
    name: 'Nasi Box Ayam Goreng Lengkuas',
    category: 'Nasi Box',
    price: 25_000,
    description: 'Nasi putih, ayam goreng lengkuas, tahu bacem, lalapan, sambal terasi.',
    recipe: [
      {
        name: 'Beras Putih',
        quantityPerPortion: 150,
        baseUnit: 'gram',
        shoppingUnit: 'kg',
        conversionFactor: 1000,
      },
      {
        name: 'Ayam Potong',
        quantityPerPortion: 125,
        baseUnit: 'gram',
        shoppingUnit: 'kg',
        conversionFactor: 1000,
      },
      {
        name: 'Lengkuas Parut',
        quantityPerPortion: 20,
        baseUnit: 'gram',
        shoppingUnit: 'kg',
        conversionFactor: 1000,
      },
      {
        name: 'Minyak Goreng',
        quantityPerPortion: 30,
        baseUnit: 'ml',
        shoppingUnit: 'liter',
        conversionFactor: 1000,
      },
      {
        name: 'Daun Salam',
        quantityPerPortion: 1,
        baseUnit: 'lembar',
      },
    ],
  },
  {
    id: 'menu-rendang-box',
    name: 'Nasi Box Rendang Daging',
    category: 'Nasi Box',
    price: 35_000,
    description: 'Nasi putih, rendang daging sapi, telur balado, sayur daun singkong, kerupuk.',
    recipe: [
      {
        name: 'Beras Putih',
        quantityPerPortion: 150,
        baseUnit: 'gram',
        shoppingUnit: 'kg',
        conversionFactor: 1000,
      },
      {
        name: 'Daging Sapi',
        quantityPerPortion: 100,
        baseUnit: 'gram',
        shoppingUnit: 'kg',
        conversionFactor: 1000,
      },
      {
        name: 'Santan Kental',
        quantityPerPortion: 60,
        baseUnit: 'ml',
        shoppingUnit: 'liter',
        conversionFactor: 1000,
      },
      {
        name: 'Telur Ayam',
        quantityPerPortion: 1,
        baseUnit: 'butir',
      },
    ],
  },
  {
    id: 'menu-snack-tradisional',
    name: 'Snack Box Kue Tradisional (Isi 3)',
    category: 'Snack Box',
    price: 15_000,
    description: 'Risoles ayam, lemper abon, puding pandan, dan air mineral gelas.',
    recipe: [],
  },
];

export const MOCK_ORDERS: readonly [MockOrder, ...MockOrder[]] = [
  {
    id: 'ord-sim-01',
    orderNumber: 'ORD-202611-0001',
    customerAlias: 'Ibu Hj. Aminah (Pengajian RT 04)',
    eventDate: '2026-11-25',
    eventTime: '09:30 WIB',
    menuId: 'menu-ayam-lengkuas',
    menuName: 'Nasi Box Ayam Goreng Lengkuas',
    portions: 100,
    totalAmount: 2_500_000,
    status: 'IN_PREPARATION',
    paymentStatus: 'PARTIALLY_PAID',
    paidAmount: 1_500_000,
    deliveryArea: 'Balai Warga RT 04, Jl. Flamboyan No. 12',
    notes: 'Sambal dipisah cup kecil. Makanan wajib tiba 30 menit sebelum acara.',
    isSynthetic: true,
  },
  {
    id: 'ord-sim-02',
    orderNumber: 'ORD-202611-0002',
    customerAlias: 'Bpk. Hendra (PT Surya Mandiri)',
    eventDate: '2026-11-25',
    eventTime: '11:30 WIB',
    menuId: 'menu-rendang-box',
    menuName: 'Nasi Box Rendang Daging',
    portions: 50,
    totalAmount: 1_750_000,
    status: 'READY',
    paymentStatus: 'PAID',
    paidAmount: 1_750_000,
    deliveryArea: 'Gedung Graha Kencana Lt. 3, Jl. Sudirman',
    notes: 'Sertakan sendok dan tisu per box. Antar lewat lobi utama.',
    isSynthetic: true,
  },
  {
    id: 'ord-sim-03',
    orderNumber: 'ORD-202611-0003',
    customerAlias: 'Ibu Sri Wahyuni (Arisan Keluarga)',
    eventDate: '2026-11-26',
    eventTime: '10:00 WIB',
    menuId: 'menu-ayam-lengkuas',
    menuName: 'Nasi Box Ayam Goreng Lengkuas',
    portions: 40,
    totalAmount: 1_000_000,
    status: 'DRAFT',
    paymentStatus: 'UNPAID',
    paidAmount: 0,
    deliveryArea: 'Perumahan Melati Indah Blok B2 No. 8',
    notes: 'Menunggu konfirmasi DP 60% sebelum belanja bahan dapur.',
    isSynthetic: true,
  },
];

export const MOCK_NOTIFICATIONS: readonly MockNotification[] = [
  {
    id: 'notif-01',
    title: 'Pengingat Masak: 100 Box Nasi Ayam',
    message: 'ORD-202611-0001 untuk Ibu Hj. Aminah harus selesai dimasak dan siap kirim pukul 09:30 WIB.',
    timeLabel: 'Hari ini · 08:00 WIB',
    category: 'JADWAL',
    adminOnly: false,
    isRead: false,
  },
  {
    id: 'notif-02',
    title: 'Daftar Kebutuhan Belanja Dapur',
    message: 'Kebutuhan besok: Beras Putih 22,5 kg, Ayam Potong 12,5 kg, Daging Sapi 5 kg.',
    timeLabel: 'Hari ini · 08:15 WIB',
    category: 'BAHAN',
    adminOnly: false,
    isRead: false,
  },
  {
    id: 'notif-03',
    title: 'Uang Muka (DP) Belum Masuk',
    message: 'Pesanan Ibu Sri Wahyuni (ORD-202611-0003) sebesar Rp 1.000.000 belum menerima DP min. Rp 600.000.',
    timeLabel: 'Hari ini · 09:00 WIB',
    category: 'KEUANGAN',
    adminOnly: true,
    isRead: false,
  },
] as const;

export function formatTanggalIndonesia(dateStr: string): string {
  try {
    const parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    const year = Number(parts[0]);
    const month = Number(parts[1]);
    const day = Number(parts[2]);
    if (Number.isNaN(year) || Number.isNaN(month) || Number.isNaN(day)) return dateStr;
    const date = new Date(year, month - 1, day);
    const hari = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'][date.getDay()];
    const bulan = [
      'Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
      'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'
    ][month - 1];
    return `${hari}, ${day} ${bulan} ${year}`;
  } catch {
    return dateStr;
  }
}

export function formatRupiah(amount: number): string {
  const safeAmount = Math.max(0, Math.round(amount));
  return `Rp ${safeAmount.toLocaleString('id-ID')}`;
}

export function calculateMinimumDp(totalAmount: number, ratio = MIN_DP_RATIO): number {
  if (totalAmount <= 0 || ratio <= 0) {
    return 0;
  }
  return Math.ceil(totalAmount * ratio);
}

export function calculateIngredientsForOrder(
  menu: MockMenuItem,
  portions: number,
): readonly CalculatedIngredientRow[] {
  if (portions <= 0 || menu.recipe.length === 0) {
    return [];
  }

  return menu.recipe.map((item) => {
    const totalBaseQuantity = item.quantityPerPortion * portions;
    let formattedShoppingAmount = `${totalBaseQuantity.toLocaleString('id-ID')} ${item.baseUnit}`;

    if (item.shoppingUnit && item.conversionFactor && totalBaseQuantity >= item.conversionFactor) {
      const converted = totalBaseQuantity / item.conversionFactor;
      const formattedNumber = Number.isInteger(converted)
        ? converted.toLocaleString('id-ID')
        : converted.toLocaleString('id-ID', { maximumFractionDigits: 2 });
      formattedShoppingAmount = `${formattedNumber} ${item.shoppingUnit}`;
    }

    return {
      name: item.name,
      totalBaseQuantity,
      baseUnit: item.baseUnit,
      formattedShoppingAmount,
    };
  });
}
