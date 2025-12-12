import { railsInfo, SECTION_LENGTH } from "./railsData"

const changesData = [{
        rail: 0,
        iPosition: 3,
        dir: 1
    },
    {
        rail: 0,
        iPosition: 11,
        dir: 1
    },
    {
        rail: 0,
        iPosition: 19,
        dir: 1
    },
    {
        rail: 1,
        iPosition: 7,
        dir: 1
    },
    {
        rail: 1,
        iPosition: 11,
        dir: 1
    },
    {
        rail: 1,
        iPosition: 19,
        dir: 1
    },
    {
        rail: 1,
        iPosition: 31,
        dir: -1
    },
    {
        rail: 1,
        iPosition: 39,
        dir: -1
    },
    {
        rail: 2,
        iPosition: 1,
        dir: 1
    },
    {
        rail: 2,
        iPosition: 9,
        dir: 1
    },
    {
        rail: 2,
        iPosition: 25,
        dir: -1
    },{
        rail: 3,
        iPosition: 11,
        dir: -1
    },
]


function createChangesData(changesDataArray){
    return changesDataArray.map((change) => {
        let x = railsInfo[change.rail].x1+SECTION_LENGTH*change.iPosition
        let y = railsInfo[change.rail].y1

        return({
            id: `c-r${change.rail}-${change.iPosition}`,
            x: x,
            y: y,
            dir: change.dir,
            pos: `M ${x} ${y} L ${SECTION_LENGTH} 0`
        })
    })
}

export const changeRailsData = createChangesData(changesData)