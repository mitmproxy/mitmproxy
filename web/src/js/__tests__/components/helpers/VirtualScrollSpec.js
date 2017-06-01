import { calcVScroll } from '../../../components/helpers/VirtualScroll'

describe('VirtualScroll', () => {

    it('should return default state without options', () => {
        expect(calcVScroll()).toEqual({start: 0, end: 0, paddingTop: 0, paddingBottom: 0})
    })

    it('should calculate position without itemHeights', () => {
        expect(calcVScroll({itemCount: 0, rowHeight: 32, viewportHeight: 400, viewportTop: 0})).toEqual({
            start: 0, end: 0, paddingTop: 0, paddingBottom: 0
        })
    })

    it('should calculate position with itemHeights', () => {
        expect(calcVScroll({itemCount: 5, itemHeights: [100, 100, 100, 100, 100],
            viewportHeight: 300, viewportTop: 0})).toEqual({
            start: 0, end: 4, paddingTop: 0, paddingBottom: 100
        })
    })
})
