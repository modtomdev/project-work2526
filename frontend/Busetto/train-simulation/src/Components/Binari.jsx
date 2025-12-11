const LENGHT = 20

const Rail = ({ x, y, rotate = 0 }) => {
  // Costruiamo la stringa del percorso
  // M = Move to (sposta la "penna" a 0,0)
  // L = Line to (disegna una linea fino a LENGHT, 0)
  // Nota: Poiché siamo dentro un <g> traslato, lavoriamo coordinate locali (partendo da 0,0)
  
  const pathData = `M 0 0 L ${LENGHT} 0`; 
  

  return (
    <g transform={`translate(${x}, ${y}) rotate(${rotate})`}>
      {/* Rotaia nera */}
      <path 
        d={pathData} 
        stroke="black" 
        strokeWidth="4" 
        fill="none" // Buona norma per i path che sono solo linee
      />
      
      {/* Pallino Inizio (Giunto) */}
      <circle cx="0" cy="0" r="3" fill="blue" />
      
      {/* Pallino Fine (Giunto) */}
      <circle cx={LENGHT} cy="0" r="3" fill="blue" />
    </g>
  );
};

const Change = ({ x, y, dir = 1}) => { // Ho aggiunto length come prop per sicurezza
  
    // Calcoliamo lo spostamento verticale:
    // Se dir è 1 (giù), offset è +30.
    // Se dir è -1 (su), offset è -30.
    const yOffset = 30 * dir;
    length = LENGHT*2

    return (
        <g transform={`translate(${x}, ${y})`}>
        <line 
            x1="0" y1="0" 
            x2={length} y2={yOffset}  // <--- Qui c'è la magia: Y finale fissa a 30
            stroke="black" 
            strokeWidth="4" 
        />
        
        {/* Il pallino blu finale deve seguire la linea */}
        <circle cx={length} cy={yOffset} r="3" fill="blue" />

        {/* Pallino comune all'origine */}
        <circle cx="0" cy="0" r="3" fill="blue" />
        </g>
    );
};

const Terminale = ({ x, y, rotate = 0 }) => {
  return (
    <g transform={`translate(${x}, ${y}) rotate(${rotate})`}>
      {/* Il quadrato di stop */}
      <rect 
        x="-5" y="-10" // Centrato rispetto alla linea
        width="20" height="20" 
        stroke="black" 
        strokeWidth="2" 
        fill="white" 
      />
      {/* La X dentro (opzionale) */}
      <line x1="-5" y1="-10" x2="15" y2="10" stroke="black" strokeWidth="1" />
      <line x1="-5" y1="10" x2="15" y2="-10" stroke="black" strokeWidth="1" />
      
      {/* Punto di connessione */}
      <circle cx="0" cy="0" r="3" fill="blue" />
    </g>
  );
};

export { Binario, Scambio, Terminale };