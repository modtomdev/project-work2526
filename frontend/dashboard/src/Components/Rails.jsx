const LENGHT = 20

const Rail = ({ x, y, rotate = 0, id}) => {
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
      <text 
        x={0}
        y={-5}
        fill="red"
        style={{
          fontSize: '7px'
        }}
      >{id}</text>
      
      {/* Pallino Inizio (Giunto) */}
      <circle cx="0" cy="0" r="3" fill="blue" />
      
      {/* Pallino Fine (Giunto) */}
      <circle cx={LENGHT} cy="0" r="3" fill="blue" />
    </g>
  );
};

const Change = ({ x, y, dir = 1, id}) => {
    // Calcoli
    const yOffset = 30 * dir;
    const length = LENGHT * 2; // Assumendo LENGHT sia una costante globale

    // Costruiamo il path: M = Start, L = End
    const pathData = `M 0 0 L ${length} ${yOffset}`;

    return (
        <g transform={`translate(${x}, ${y})`}>
            {/* Binario (Scambio) */}
            <path 
                d={pathData} 
                stroke="black" 
                strokeWidth="4" 
                fill="none" 
            />
            <text
              x={30}
              y={15*dir}
              fill="red"
              style={{
                fontSize: '7px'
              }}
            >{id}</text>
            
            {/* Pallino Fine (segue l'offset) */}
            <circle cx={length} cy={yOffset} r="3" fill="blue" />

            {/* Pallino Inizio */}
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

export { Rail, Change, Terminale };