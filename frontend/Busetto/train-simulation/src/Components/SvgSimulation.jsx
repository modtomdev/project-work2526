import './svgSimulation.css'
import { Rail, Change, Terminale } from './Rails'
import { straightRailsData } from '../assets/railsData'
import { changeRailsData } from '../assets/changesData'
import { Wagon } from './Wagon'
import React, { useState, useEffect } from 'react';

// Array elementi Rails
const railsElement = straightRailsData.map((rail) => {
    return <Rail key={rail.id} x={rail.x} y={rail.y} id={rail.id}/>
})

// Array elementi Changes
const changeElement = changeRailsData.map((change) => {
    return <Change key={change.id} x={change.x} y={change.y} dir={change.dir} id={change.id}/>
})

const Trip1 = straightRailsData.slice(0,10)
const Trip2 = straightRailsData.slice(straightRailsData.length-10, straightRailsData.length)

const Trips = [Trip1, Trip2]

function GenerateMockSnapshot(index){

    const nWagons = 2
    const colors = ['red', 'green', 'blue', 'yellow']

    let wagonsInfo = []

    for (let i = 0; i < nWagons; i++) {
        wagonsInfo.push({
            id: i,
            color: colors[i],
            pos: Trips[i][index].pos
        })
        
    }

    console.log(wagonsInfo)

    return wagonsInfo
}




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

    let currentSnapshot = GenerateMockSnapshot(currentIndex)
    console.log(currentSnapshot)

    let WagonsElements = currentSnapshot.map((trip) => {

        return <Wagon
            pathData={trip.pos} 
            x={trip.x} 
            y={trip.y} 
            duration={TEMPO_PERCORRENZA}
            color={trip.color}
        />
    })

    return(
        <>
            <div className='sfondo'>
                <svg className='tavolozza' width={900} height={300}>
                    
                    {/* Disegna tutti i binari */}
                    {railsElement}
                    {changeElement}
                    

                    {/* {WagonsElements} */}

                    
                </svg>
            </div>
        </>
    )
}