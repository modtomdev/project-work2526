import './svgSimulation.css'
import { Rail, Change, Terminale } from './Binari'
import { straightRailData, changeRailsData } from '../assets/railData'
import { Wagon } from './Wagon'
import React, { useState, useEffect } from 'react';

const railsElement = straightRailData.map((rail) => {
    return <Rail key={rail.id} x={rail.x} y={rail.y}/>
})

const changeElement = changeRailsData.map((change) => {
    return <Change key={change.id} x={change.x} y={change.y} dir={change.dir} />
})


const TEMPO_PERCORRENZA = 500; 

export default function SvgSimulation(){
    
    // Stato per l'indice del binario corrente
    const [currentIndex, setCurrentIndex] = useState(0);

    // LOGICA DI INCREMENTO DELL'INDICE (Timer)
    useEffect(() => {
        const interval = setInterval(() => {
            setCurrentIndex((prevIndex) => {
                // Passa all'indice successivo in loop
                return (prevIndex + 1) % straightRailData.length;
            });
        }, TEMPO_PERCORRENZA);

        return () => clearInterval(interval);
    }, []); 

    // Recupera i dati del binario ATTIVO
    const currentRail = straightRailData[currentIndex];

    return(
        <>
            <div className='sfondo'>
                <svg className='tavolozza' width={900} height={300}>
                    
                    {/* Disegna tutti i binari */}
                    {railsElement}
                    {changeElement}

                    {/* Il Vagone Dinamico: riceve i dati del binario attivo */}
                    <Wagon 
                        pathData={currentRail.pos} 
                        x={currentRail.x} 
                        y={currentRail.y} 
                        duration={TEMPO_PERCORRENZA}
                    />
                </svg>
            </div>
        </>
    )
}