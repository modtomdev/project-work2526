

// --- CONFIGURAZIONE ---
export const SECTION_LENGTH = 20;

function createRailsData(start_x, start_y, rotate, type, total_sections, key_start){
    return Array.from({ length: total_sections }, (_, index) => {

        let x = start_x + (index * SECTION_LENGTH)
        let y = start_y

        return {
            id: `${key_start}-${index}`,            // ID univoco (es. t1-0, t1-1, t1-2...)
            type: {type},                       // Tipo di binario (deve corrispondere al tuo switch case)
            x: x,  // Calcolo progressivo della X
            y: y,                             // Y fissa
            rotate: {rotate},                               // Rotazione 0 (dritto)
            pos: `M ${x} ${y} L ${SECTION_LENGTH+x} ${y}`
        }
    })
}

export const railsInfo = [
    {
        id: 'r0',
        x1: 30,
        y1: 100
    },
    {
        id: 'r1',
        x1: 30,
        y1: 130,
    },
    {
        id: 'r2',
        x1: 30+9*20,
        y1: 160
    },
    {
        id: 'r3',
        x1: 30+20*20,
        y1: 190
    }
]


const rail1 = createRailsData(railsInfo[0].x1, railsInfo[0].y1, 0, 'straight', 42, 'r0')
const rail2 = createRailsData(railsInfo[1].x1, railsInfo[1].y1, 0, 'straight', 42, 'r1')
const rail3 = createRailsData(railsInfo[2].x1, railsInfo[2].y1, 0, 'straight', 25, 'r2')
const rail4 = createRailsData(railsInfo[3].x1, railsInfo[3].y1, 0, 'straight', 11, 'r3')

export const straightRailsData = [...rail1, ...rail2, ...rail3, ...rail4]


