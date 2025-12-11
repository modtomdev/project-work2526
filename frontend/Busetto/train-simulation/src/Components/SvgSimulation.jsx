import './svgSimulation.css'
import { Rail, Change, Terminale } from './Binari'
import { straightRailsData } from '../assets/railsData'
import { changeRailsData } from '../assets/changesData'
import { Wagon } from './Wagon'
import React, { useState, useEffect } from 'react';

const railsElement = straightRailsData.map((rail) => {
    return <Rail key={rail.id} x={rail.x} y={rail.y}/>
})

const changeElement = changeRailsData.map((change) => {
    return <Change key={change.id} x={change.x} y={change.y} dir={change.dir} />
})

const Trip1 = straightRailsData.slice(0,10)
const Trip2 = straightRailsData.slice(straightRailsData.length-10, straightRailsData.length)


const TEMPO_PERCORRENZA = 500;

export default function SvgSimulation(){
    
    // Stato per l'indice del binario corrente
    const [currentIndex, setCurrentIndex] = useState(0);

    // LOGICA DI INCREMENTO DELL'INDICE (Timer)
    useEffect(() => {
        const interval = setInterval(() => {
            setCurrentIndex((prevIndex) => {
                // Passa all'indice successivo in loop
                return (prevIndex + 1) % 10;
            });

        }, TEMPO_PERCORRENZA);

        return () => clearInterval(interval);
    }, []); 

    // Recupera i dati del binario ATTIVO

    let AllTrip = [Trip1[currentIndex],Trip2[currentIndex]]
    console.log(AllTrip)

    let WagonsElements = AllTrip.map((trip) => {
        console.log(trip.pos)

        return <Wagon
            pathData={trip.pos} 
            x={trip.x} 
            y={trip.y} 
            duration={TEMPO_PERCORRENZA}
        />
    })

    return(
        <>
            <div className='sfondo'>
                <svg className='tavolozza' width={900} height={300}>
                    
                    {/* Disegna tutti i binari */}
                    {railsElement}
                    {changeElement}

                    {/* Il Vagone Dinamico: riceve i dati del binario attivo */}
                    {/* <Wagon 
                        pathData={currentRail.pos} 
                        x={currentRail.x} 
                        y={currentRail.y} 
                        duration={TEMPO_PERCORRENZA}
                    /> */}
                    

                    {WagonsElements}

                    
                </svg>
            </div>
        </>
    )
}