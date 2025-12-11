import { useState, useEffect } from 'react';

// Il componente Vagone riceve i dati del binario corrente e la durata dell'animazione.
export const Wagon = ({ pathData, x, y, duration = 3000 }) => {
    // Stato per la percentuale di percorrenza (0% o 100%)
    const [progress, setProgress] = useState(0); 
    // Stato per attivare/disattivare la transizione (per il "teletrasporto" iniziale)
    const [isMoving, setIsMoving] = useState(false); 

    useEffect(() => {
        // 1. FASE DI RESET (Teletrasporto a 0%)
        // Disattiviamo l'animazione e portiamo il treno all'inizio del nuovo binario.
        setIsMoving(false); 
        setProgress(0);     

        // 2. FASE DI PARTENZA (Avvio animazione)
        // Aspettiamo 50ms prima di far partire l'animazione fluida.
        const timerStart = setTimeout(() => {
            setIsMoving(true); // Riattiva la transizione CSS
            setProgress(100);  // Dice al CSS: "Vai alla fine!"
        }, 50);

        return () => clearTimeout(timerStart);
        
    }, [pathData, x, y, duration]); // L'effetto riparte quando cambiano questi dati.

    return (
        // Spostiamo l'intero vagone nella posizione iniziale del binario (x, y)
        <g>
            <rect 
                width={20}
                height={10}
                fill="red"
                rx={4}
                x={-10} // Metà larghezza per centrare sulla linea
                y={-5}  // Metà altezza per centrare sulla linea
                style={{
                    // Aggancia il rettangolo alla forma del path
                    offsetPath: `path("${pathData}")`,
                    
                    // Imposta la posizione dinamica
                    offsetDistance: `${progress}%`,
                    
                    offsetRotate: 'auto', // Ruota automaticamente lungo la curva

                    // Transizione CSS: fluida se isMoving=true, istantanea se false
                    transition: isMoving 
                                ? `offset-distance ${duration}ms linear` 
                                : 'none'
                }}
            />
        </g>
    );
};