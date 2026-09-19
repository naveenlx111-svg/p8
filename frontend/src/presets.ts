export interface Target {
  platform?: 'web' | 'android'
  goal: string
  url: string
  successUrl: string
  successText: string
  maxSteps?: string
  deviceSerial?: string
  packageName?: string
  activity?: string
  apkId?: string
  apkName?: string
}

// Examples only fill the form; the agent still receives nothing but the URL and goal.
export const PRESETS: { name: string; t: Target }[] = [
  {
    name: 'NovaMart demo shop (planted defects)',
    t: { goal: 'Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.', url: 'http://127.0.0.1:4173/', successUrl: '', successText: '' },
  },
  {
    name: 'NovaMart candidate release (UX regression)',
    t: { goal: 'Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.', url: 'http://127.0.0.1:4173/?release=candidate', successUrl: '', successText: '' },
  },
  {
    name: 'SauceDemo · standard user',
    t: { goal: 'Log in with username standard_user and password secret_sauce, add the Sauce Labs Backpack to the cart, and reach checkout.', url: 'https://www.saucedemo.com/', successUrl: '', successText: '' },
  },
  {
    name: 'SauceDemo · problem user (real bugs)',
    t: { goal: 'Log in with username problem_user and password secret_sauce, add the Sauce Labs Backpack to the cart, go to checkout, enter first name Asha, last name Rao and postal code 560001, and reach the checkout overview.', url: 'https://www.saucedemo.com/', successUrl: 'checkout-step-two', successText: '' },
  },
  {
    name: 'Amazon.in (live site, long journey)',
    t: { goal: 'Search for a boAt wired earphone, open its product page, add it to the cart, and open the cart.', url: 'https://www.amazon.in/', successUrl: 'cart', successText: 'Subtotal' },
  },
  {
    name: 'Demoblaze store',
    t: { goal: 'Find the Samsung galaxy s6, add it to the cart, and open the cart.', url: 'https://demoblaze.com/', successUrl: 'cart', successText: 'Samsung galaxy s6' },
  },
]
