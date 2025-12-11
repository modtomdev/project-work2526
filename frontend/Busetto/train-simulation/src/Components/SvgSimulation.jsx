import './svgSimulation.css'
import { Rail, Change, Terminale } from './Binari'
import { straightRailData, changeRailsData } from '../assets/railData'

const railsElement = straightRailData.map((rail) => {
    return <Rail key={rail.id} x={rail.x} y={rail.y}/>
})

const changeElement = changeRailsData.map((change) => {
    return <Change key={change.id} x={change.x} y={change.y} dir={change.dir} />
})


export default function SvgSimulation(){
    return(
    <>
        <div className='sfondo'>
    
            <svg className='tavolozza' width={900} height={300}>
                {railsElement}
                {changeElement}


                



            </svg>

        </div>
    </>
    )
}