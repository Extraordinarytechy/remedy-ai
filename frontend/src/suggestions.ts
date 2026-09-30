/*
 * Type-ahead suggestions. Everything here is bundled with the site: nothing is sent anywhere
 * while the user types, and no AI is involved. Suggestions never restrict input.
 *
 * Covered products come from backend/knowledge/*.json at build time, so the "has a verified
 * program" label can only appear for a product a knowledge record actually names.
 */

export interface Suggestion {
  value: string;
  note?: string;
}

interface KnowledgeRecord {
  category?: string;
  issuer_or_brand?: string;
  applicable_devices?: string[];
  display_names?: string[];
  listed_on_apple_service_programs_index?: boolean;
}

const records = Object.values(
  import.meta.glob<KnowledgeRecord>('../../backend/knowledge/**/*.json', { eager: true, import: 'default' }),
);

const brandOf = (issuer?: string) => (issuer ?? '').replace(/\s+Inc\.?$/, '').trim();

/** Products named by a manufacturer program record. Only currently listed programs get the label. */
const PROGRAM_PRODUCTS: Suggestion[] = records
  .filter((r) => r.category === 'manufacturer_service_program')
  .flatMap((r) =>
    (r.display_names ?? r.applicable_devices ?? []).map((d) => ({
      value: `${brandOf(r.issuer_or_brand)} ${d}`.trim(),
      note: r.listed_on_apple_service_programs_index === false ? 'program no longer listed' : 'has a verified program',
    })),
  );

/** Newest models named by a manufacturer warranty record (e.g. iPhone 18 Pro). */
const WARRANTY_PRODUCTS: Suggestion[] = records
  .filter((r) => r.category === 'manufacturer_warranty')
  .flatMap((r) => (r.display_names ?? []).map((value) => ({ value, note: 'in 1-year warranty if new (US)' })));

export const COVERED_PRODUCTS: Suggestion[] = [...WARRANTY_PRODUCTS, ...PROGRAM_PRODUCTS];

const COMMON_PRODUCTS = [
  'Apple iPhone 17', 'Apple iPhone 16', 'Apple iPhone 15', 'Apple iPhone 14', 'Apple iPhone 14 Pro', 'Apple iPhone 13',
  'Apple iPad', 'Apple MacBook Air', 'Apple AirPods Pro',
  'Samsung Galaxy S24', 'Samsung Galaxy S23', 'Samsung 55-inch 4K TV', 'Samsung washing machine',
  'Google Pixel 8', 'Google Pixel 7',
  'Sony WH-1000XM5 headphones', 'Sony WH-1000XM4 headphones', 'Sony 55-inch Bravia TV', 'Sony PlayStation 5',
  'LG 55-inch OLED TV', 'LG fridge freezer', 'Bose QuietComfort headphones', 'Dell XPS laptop', 'HP laptop',
  'Lenovo ThinkPad laptop', 'Microsoft Xbox Series X', 'Nintendo Switch', 'Dyson vacuum cleaner', 'OnePlus phone',
];

export const PRODUCTS: Suggestion[] = [
  ...COVERED_PRODUCTS,
  ...COMMON_PRODUCTS.filter((p) => !COVERED_PRODUCTS.some((c) => c.value.toLowerCase() === p.toLowerCase())).map((value) => ({ value })),
];

const STORES_BY_COUNTRY: Record<string, string[]> = {
  US: ['Best Buy', 'Amazon.com', 'Walmart', 'Target', 'Costco', 'Apple Store', 'Home Depot', "Lowe's", 'B&H Photo'],
  GB: ['Currys', 'Argos', 'John Lewis', 'Amazon.co.uk', 'Apple Store', 'AO.com', 'Very', 'Richer Sounds', 'Tesco'],
  IN: ['Amazon.in', 'Flipkart', 'Croma', 'Reliance Digital', 'Vijay Sales', 'Apple Store'],
  CA: ['Best Buy Canada', 'Amazon.ca', 'Walmart Canada', 'Costco', 'Canadian Tire', 'Apple Store'],
  AU: ['JB Hi-Fi', 'Harvey Norman', 'The Good Guys', 'Amazon.com.au', 'Officeworks', 'Apple Store'],
};

export function storesFor(country: string): Suggestion[] {
  return (STORES_BY_COUNTRY[country] ?? Object.values(STORES_BY_COUNTRY).flat())
    .filter((v, i, a) => a.indexOf(v) === i)
    .map((value) => ({ value }));
}

export const PAYMENTS: Suggestion[] = [
  'Visa Infinite', 'Visa Signature', 'Visa credit card (other)', 'Mastercard', 'American Express', 'Debit card',
  'Cash', 'PayPal', 'Bank transfer',
].map((value) => ({ value }));

const FAULTS: { match: RegExp; phrases: string[] }[] = [
  {
    match: /iphone|phone|pixel|galaxy s|oneplus/i,
    phrases: [
      'Rear camera shows a black screen with no preview',
      'No sound from the earpiece during calls',
      'Battery drains very fast or the phone shuts down',
      'Screen flickers or shows lines',
      'Phone will not charge',
      'Face ID or fingerprint stopped working',
    ],
  },
  {
    match: /tv|television|oled|bravia|monitor/i,
    phrases: [
      'Lines or flicker across the screen',
      'Backlight flickers or part of the screen is dark',
      'No picture but sound works',
      'TV will not turn on',
    ],
  },
  {
    match: /headphone|airpods|earbud|quietcomfort|wh-1000/i,
    phrases: [
      'Hinge cracked during normal use',
      'One side has no sound',
      'Noise cancelling stopped working',
      'Will not charge or hold a charge',
    ],
  },
  {
    match: /mac mini|imac|mac studio/i,
    phrases: ['Will not turn on (no power)', 'Turns off by itself', 'No display output', 'Fan is very loud'],
  },
  {
    match: /laptop|macbook|xps|thinkpad|computer/i,
    phrases: ['Keyboard keys stopped working', 'Screen has lines or flickers', 'Will not turn on', 'Battery swollen or not charging'],
  },
  {
    match: /washing|fridge|freezer|vacuum|dyson|dishwasher/i,
    phrases: ['Stopped working completely', 'Motor makes a loud noise', 'Leaks water', 'Error code on the display'],
  },
];

export function faultsFor(product: string): Suggestion[] {
  const hit = FAULTS.filter((f) => f.match.test(product)).flatMap((f) => f.phrases);
  const list = hit.length ? hit : ['Stopped working completely', 'Will not turn on', 'Will not charge', 'Makes a loud noise'];
  return list.map((value) => ({ value }));
}

/** Case-insensitive match anywhere in the text; best matches (prefix) first; at most `limit`. */
export function filterSuggestions(items: Suggestion[], query: string, limit = 6): Suggestion[] {
  const q = query.trim().toLowerCase();
  if (!q) return items.slice(0, limit);
  return items
    .map((s) => ({ s, i: s.value.toLowerCase().indexOf(q) }))
    .filter((x) => x.i >= 0 && x.s.value.toLowerCase() !== q)
    .sort((a, b) => a.i - b.i)
    .slice(0, limit)
    .map((x) => x.s);
}
