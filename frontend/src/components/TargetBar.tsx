export interface Target {
  goal: string
  url: string
  successUrl: string
  successText: string
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
    name: 'Demoblaze store',
    t: { goal: 'Find the Samsung galaxy s6, add it to the cart, and open the cart.', url: 'https://demoblaze.com/', successUrl: 'cart', successText: 'Samsung galaxy s6' },
  },
]

interface Props {
  target: Target
  setTarget: (t: Target) => void
  disabled: boolean
}

const input = 'rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none disabled:bg-slate-50'

export function TargetBar({ target, setTarget, disabled }: Props) {
  const set = (k: keyof Target) => (e: React.ChangeEvent<HTMLInputElement>) => setTarget({ ...target, [k]: e.target.value })
  return (
    <div className="target-bar flex flex-wrap items-center gap-2 px-5 py-2 text-xs text-slate-300">
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
      <select aria-label="Example targets" disabled={disabled} value="" onChange={e => {
        const preset = PRESETS[Number(e.target.value)]
        if (preset) setTarget(preset.t)
      }} className="target-examples rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800">
        <option value="">Examples…</option>
        {PRESETS.map((preset, index) => <option key={preset.name} value={index}>{preset.name}</option>)}
      </select>
    </div>
  )
}
