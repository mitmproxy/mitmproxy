/* _GlobalPrefix_ */
this.gbar_=this.gbar_||{};
(function(_) {
  var window=this;
  
/* _Module_:sy25 */
  try {
    var Mn=function(){};
    _.y(Mn,Error);
    _.Nn=function() {
      this.b="pending";
      this.B=[];
      this.w=this.C=void 0
    };
    _.fe(_.Nn);
    var On=function() {
      _.qa.call(this,"Multiple attempts to set the state of this Result")
    };
    _.y(On,_.qa);
    _.Nn.prototype.ta=function() {
      return this.C
    };
    _.Pn=function(a,c,d) {
      "pending"==a.b?a.B.push( {
        hb:c,scope:d||null
      }
      ):c.call(d,a)
    };
    _.Nn.prototype.A=function(a) {
      if("pending"==this.b)this.C=a,this.b="success",Qn(this);
      else if(!Rn(this))throw new On;
    };
    _.Nn.prototype.o=function(a) {
      if("pending"==this.b)this.w=a,this.b="error",Qn(this);
      else if(!Rn(this))throw new On;
    };
    var Qn=function(a) {
      var c=a.B;
      a.B=[];
      for(var d=0;d<c.length;d++) {
        var e=c[d];
        e.hb.call(e.scope,a)
      }
      
    };
    _.Nn.prototype.cancel=function() {
      return"pending"==this.b?(this.o(new Mn),!0):!1
    };
    var Rn=function(a) {
      return"error"==a.b&&a.w instanceof Mn
    };
    _.Nn.prototype.then=function(a,c,d) {
      var e,f,g=new _.ie(function(a,c) {
        e=a;
        f=c
      }
      );
      _.Pn(this,function(a) {
        Rn(a)?g.cancel():"success"==a.b?e(a.ta()):"error"==a.b&&f(a.w)
      }
      );
      return g.then(a,c,d)
    };
    
  }
  catch(e) {
    _._DumpException(e)
  }
