// Pemakaian: npm run vouchers -- <paket> <jumlah>   contoh: npm run vouchers -- 7d 10
import * as db from '../lib/db.js';
import { PLANS } from '../lib/config.js';

const [plan = '1d', count = '1'] = process.argv.slice(2);
if (!PLANS[plan]) {
  console.error(`Paket tidak dikenal. Pilihan: ${Object.keys(PLANS).join(', ')}`);
  process.exit(1);
}
db.load();
const codes = db.createVouchers(plan, Math.min(parseInt(count, 10) || 1, 500));
console.log(`${codes.length} voucher ${PLANS[plan].label} ($${PLANS[plan].priceUsd}):`);
for (const c of codes) console.log(c);
