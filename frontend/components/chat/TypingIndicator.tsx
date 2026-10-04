
export function TypingIndicator() {

  return (

    <div style={{ display: 'flex', gap: 4, padding: '10px 14px' }}>

      {[0, 1, 2].map((i) => (

        <span key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: 'rgba(247,245,240,0.4)', animation: `bounce 1.2s infinite ${i * 0.15}s` }} />

      ))}

      <style>{`@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-4px); opacity: 1; } }`}</style>

    </div>

  )

}

