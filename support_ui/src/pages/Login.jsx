import { createElement, useState } from "react";
import { ArrowRight, BadgeCheck, Bot, Building2, Phone, ShieldCheck, Sparkles } from "lucide-react";

const TOPICS = ["Admissions", "Departments", "Hostel", "Placements", "Fees", "Events"];
const FEATURES = [
  { icon: ShieldCheck, label: "Verified" },
  { icon: Building2, label: "Campus" },
  { icon: Sparkles, label: "Instant" },
];

export default function Login({ onLogin }) {
  const [phone, setPhone] = useState("");

  return (
    <div className="screen-bg flex min-h-screen items-center justify-center px-4 py-8 text-slate-100">
      <div className="relative z-10 grid w-full max-w-5xl items-stretch gap-5 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="glass-panel relative overflow-hidden rounded-[2rem] p-6 sm:p-8">
          <div className="flex items-center gap-3">
            <div className="brand-mark flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-base font-black text-white">
              GN
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-teal-200/75">
                Support Console
              </p>
              <h1 className="mt-1 text-2xl font-black tracking-tight text-shine sm:text-3xl">
                GNDEC Assistant
              </h1>
            </div>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {FEATURES.map((feature) => (
              <div key={feature.label} className="glass-card rounded-2xl px-4 py-3">
                {createElement(feature.icon, { className: "h-4 w-4 text-teal-200" })}
                <p className="mt-2 text-sm font-semibold text-white">{feature.label}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-rose-500/15 text-rose-200 ring-1 ring-rose-300/20">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">Guru Nanak Dev Engineering College</p>
                <p className="text-xs text-slate-400">Ludhiana, Punjab</p>
              </div>
            </div>
            <p className="mt-5 text-sm leading-6 text-slate-300">
              Get answers for admissions, departments, facilities, fees, placements, events, and campus services.
            </p>
          </div>
        </section>

        <section className="glass-panel rounded-[2rem] p-6 shadow-2xl sm:p-8">
          <div className="mb-7 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-rose-200/80">
                Login
              </p>
              <h2 className="mt-2 text-2xl font-black tracking-tight text-white">
                Start a conversation
              </h2>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/[0.08] ring-1 ring-white/10">
              <BadgeCheck className="h-5 w-5 text-teal-200" />
            </div>
          </div>

          <div className="space-y-5">
            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                <Phone className="h-3.5 w-3.5" />
                Phone Number
              </span>
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && phone && onLogin(phone)}
                placeholder="e.g. 9876543210"
                className="glass-input w-full rounded-2xl px-4 py-3.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-rose-300/50 focus:ring-4 focus:ring-rose-500/10"
              />
            </label>

            <button
              onClick={() => phone && onLogin(phone)}
              disabled={!phone}
                className={`flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-3.5 text-sm font-bold active:scale-[0.98]
                ${phone
                  ? "bg-rose-600 text-white shadow-lg shadow-rose-500/25 hover:bg-rose-500"
                  : "cursor-not-allowed bg-white/[0.06] text-slate-600"
                }`}
            >
              Continue
              <ArrowRight className="h-4 w-4" />
            </button>

            <div className="border-t border-white/10 pt-5">
              <div className="flex flex-wrap gap-2">
                {TOPICS.map((t) => (
                  <span
                    key={t}
                    className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-[11px] font-medium text-slate-300"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <p className="mt-5 text-center text-[11px] text-slate-500">
            Powered by GNDEC AI | gndec.ac.in
          </p>
        </section>
      </div>
    </div>
  );
}
