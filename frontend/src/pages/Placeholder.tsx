export default function Placeholder({ title }: { title: string }) {
  return (
    <section className="space-y-2">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-muted">This module is being assembled from the verified evidence ledger.</p>
    </section>
  )
}
