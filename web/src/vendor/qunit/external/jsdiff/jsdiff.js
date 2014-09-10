/*
 * Javascript Diff Algorithm
 *  By John Resig (http://ejohn.org/)
 *  Modified by Chu Alan "sprite"
 *
 * Released under the MIT license.
 *
 * More Info:
 *  http://ejohn.org/projects/javascript-diff-algorithm/
 *
 * Usage: QUnit.diff(expected, actual)
 *
 * QUnit.diff( "the quick brown fox jumped over", "the quick fox jumps over" ) == "the  quick <del>brown </del> fox <del>jumped </del><ins>jumps </ins> over"
 */
QUnit.diff = (function() {
	var hasOwn = Object.prototype.hasOwnProperty;

	/*jshint eqeqeq:false, eqnull:true */
	function diff( o, n ) {
		var i,
			ns = {},
			os = {};

		for ( i = 0; i < n.length; i++ ) {
			if ( !hasOwn.call( ns, n[ i ] ) ) {
				ns[ n[ i ] ] = {
					rows: [],
					o: null
				};
			}
			ns[ n[ i ] ].rows.push( i );
		}

		for ( i = 0; i < o.length; i++ ) {
			if ( !hasOwn.call( os, o[ i ] ) ) {
				os[ o[ i ] ] = {
					rows: [],
					n: null
				};
			}
			os[ o[ i ] ].rows.push( i );
		}

		for ( i in ns ) {
			if ( hasOwn.call( ns, i ) ) {
				if ( ns[ i ].rows.length === 1 && hasOwn.call( os, i ) && os[ i ].rows.length === 1 ) {
					n[ ns[ i ].rows[ 0 ] ] = {
						text: n[ ns[ i ].rows[ 0 ] ],
						row: os[ i ].rows[ 0 ]
					};
					o[ os[ i ].rows[ 0 ] ] = {
						text: o[ os[ i ].rows[ 0 ] ],
						row: ns[ i ].rows[ 0 ]
					};
				}
			}
		}

		for ( i = 0; i < n.length - 1; i++ ) {
			if ( n[ i ].text != null && n[ i + 1 ].text == null && n[ i ].row + 1 < o.length && o[ n[ i ].row + 1 ].text == null &&
				n[ i + 1 ] == o[ n[ i ].row + 1 ] ) {

				n[ i + 1 ] = {
					text: n[ i + 1 ],
					row: n[ i ].row + 1
				};
				o[ n[ i ].row + 1 ] = {
					text: o[ n[ i ].row + 1 ],
					row: i + 1
				};
			}
		}

		for ( i = n.length - 1; i > 0; i-- ) {
			if ( n[ i ].text != null && n[ i - 1 ].text == null && n[ i ].row > 0 && o[ n[ i ].row - 1 ].text == null &&
				n[ i - 1 ] == o[ n[ i ].row - 1 ] ) {

				n[ i - 1 ] = {
					text: n[ i - 1 ],
					row: n[ i ].row - 1
				};
				o[ n[ i ].row - 1 ] = {
					text: o[ n[ i ].row - 1 ],
					row: i - 1
				};
			}
		}

		return {
			o: o,
			n: n
		};
	}

	return function( o, n ) {
		o = o.replace( /\s+$/, "" );
		n = n.replace( /\s+$/, "" );

		var i, pre,
			str = "",
			out = diff( o === "" ? [] : o.split( /\s+/ ), n === "" ? [] : n.split( /\s+/ ) ),
			oSpace = o.match( /\s+/g ),
			nSpace = n.match( /\s+/g );

		if ( oSpace == null ) {
			oSpace = [ " " ];
		} else {
			oSpace.push( " " );
		}

		if ( nSpace == null ) {
			nSpace = [ " " ];
		} else {
			nSpace.push( " " );
		}

		if ( out.n.length === 0 ) {
			for ( i = 0; i < out.o.length; i++ ) {
				str += "<del>" + out.o[ i ] + oSpace[ i ] + "</del>";
			}
		} else {
			if ( out.n[ 0 ].text == null ) {
				for ( n = 0; n < out.o.length && out.o[ n ].text == null; n++ ) {
					str += "<del>" + out.o[ n ] + oSpace[ n ] + "</del>";
				}
			}

			for ( i = 0; i < out.n.length; i++ ) {
				if ( out.n[ i ].text == null ) {
					str += "<ins>" + out.n[ i ] + nSpace[ i ] + "</ins>";
				} else {

					// `pre` initialized at top of scope
					pre = "";

					for ( n = out.n[ i ].row + 1; n < out.o.length && out.o[ n ].text == null; n++ ) {
						pre += "<del>" + out.o[ n ] + oSpace[ n ] + "</del>";
					}
					str += " " + out.n[ i ].text + nSpace[ i ] + pre;
				}
			}
		}

		return str;
	};
}());
