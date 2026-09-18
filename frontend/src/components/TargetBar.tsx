export interface Target {
  goal: string
  url: string
  successUrl: string
  successText: string
  maxSteps?: string
}

// Examples only fill the form; the agent still receives nothing but the URL and the goal text.
export const PRESETS: { name: string; t: Target }[] = [
  {
    name: 'NovaMart demo shop (planted defects)',
    t: { goal: 'Find the Nova headphones under ₹3,000, add them to cart, and reach checkout.', url: 'http://127.0.0.1:4173/', successUrl: '', successText: '' },
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
    t: { goal: 'Search for a boAt wired earphone under ₹1,000, open its product page, add it to the cart, and open the cart.', url: 'https://www.amazon.in/', successUrl: 'cart', successText: 'Subtotal' },
  },
  {
    name: 'Demoblaze store',
    t: { goal: 'Find the Samsung galaxy s6, add it to the cart, and open the cart.', url: 'https://demoblaze.com/', successUrl: 'cart', successText: 'Samsung galaxy s6' },
  },
]

interface Props {
  target: Target
  setTarget: (t: Target) => void
  disabled: boolean
}

const input = 'rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none disabled:bg-slate-50'

export function TargetBar({ target, setTarget, disabled }: Props) {
  const set = (k: keyof Target) => (e: React.ChangeEvent<HTMLInputElement>) => setTarget({ ...target, [k]: e.target.value })
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50 px-5 py-2 text-xs text-slate-600">
      <label className="flex items-center gap-1.5 font-semibold">
        Target URL
        <input aria-label="Target URL" value={target.url} onChange={set('url')} disabled={disabled} placeholder="https://…" className={`${input} w-72 font-mono`} />
      </label>
      <label className="flex items-center gap-1.5 font-semibold" title="Optional acceptance criteria. Leave empty to derive them from the goal.">
        Done when URL contains
        <input aria-label="Success URL contains" value={target.successUrl} onChange={set('successUrl')} disabled={disabled} placeholder="auto" className={`${input} w-40`} />
      </label>
      <label className="flex items-center gap-1.5 font-semibold">
        and page shows
        <input aria-label="Success text" value={target.successText} onChange={set('successText')} disabled={disabled} placeholder="auto" className={`${input} w-40`} />
      </label>
      <label className="flex items-center gap-1.5 font-semibold" title="Safety ceiling. Runs normally stop on verified success or when the agent stalls.">
        Max steps
        <input aria-label="Max steps" value={target.maxSteps ?? ''} onChange={set('maxSteps')} disabled={disabled} placeholder="100" inputMode="numeric" className={`${input} w-16`} />
      </label>
      <select
        aria-label="Example targets"
        disabled={disabled}
        value=""
        onChange={e => {
          const p = PRESETS[Number(e.target.value)]
          if (p) setTarget(p.t)
        }}
        className="ml-auto rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800"
      >
        <option value="">Examples…</option>
        {PRESETS.map((p, i) => <option key={p.name} value={i}>{p.name}</option>)}
      </select>
    </div>
  )
}
