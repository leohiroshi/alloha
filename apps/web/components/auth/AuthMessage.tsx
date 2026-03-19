type AuthMessageProps = {
  title: string;
  body: string;
  variant?: "success" | "error" | "info";
};

const variantClasses: Record<NonNullable<AuthMessageProps["variant"]>, string> = {
  success: "border-[#ffb47c]/20 bg-[#ff7a26]/10 text-[#ffe7da]",
  error: "border-[#ff7a2f]/22 bg-[#ff5a1f]/8 text-[#ffd8c7]",
  info: "border-white/8 bg-white/[0.02] text-white/68",
};

export function AuthMessage({ title, body, variant = "success" }: AuthMessageProps) {
  return (
    <div className={`rounded-[18px] border px-4 py-3 ${variantClasses[variant]}`}>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-sm leading-6">{body}</p>
    </div>
  );
}
