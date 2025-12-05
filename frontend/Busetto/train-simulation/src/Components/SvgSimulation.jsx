import './svgSimulation.css'
import { Binario, Scambio, Terminale } from './Binari'
import { straightRailData, changeRailsData } from '../assets/railData'

const railsElement = straightRailData.map((rail) => {
    return <Binario key={rail.id} x={rail.x} y={rail.y}/>
})

const changeElement = changeRailsData.map((change) => {
    return <Scambio key={change.id} x={change.x} y={change.y} dir={change.dir} />
})


export default function SvgSimulation(){
    return(
    <>
        <div className='sfondo'>
    
            <svg className='tavolozza' width={900} height={300}>
                {railsElement}
                {changeElement}
                
                {/* <path 
                    id="binario_fantasma_1"
                    d="M 30 100 L 870 100" 
                    fill="none" 
                    stroke="red"     // Mettilo ROSSO per vederlo mentre sviluppi (debug)
                    strokeWidth="2"  // Poi lo metterai "transparent" o rimuoverai stroke
                /> */}


                



            </svg>

        </div>
    </>
    )
}