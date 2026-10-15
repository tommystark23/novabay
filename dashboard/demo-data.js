// Sample data only. Replace by writing novabay-live.js from your own sync.
(function(){
  const h = n => new Date(Date.now()+n*3600e3).toISOString();
  window.NOVABAY_LIVE = {
    ok: true, source: "demo", at: new Date().toISOString(), shop: "Demo Card Shop",
    active: [
      {item:"DEMO-1001",title:"1999 Topps Chrome Rookie #201",type:"Auction",price:14.50,bids:3,watchers:6,end:h(20)},
      {item:"DEMO-1002",title:"2020 Prizm Silver Rookie",type:"Auction",price:9.95,bids:1,watchers:4,end:h(0.6)},
      {item:"DEMO-1003",title:"Holo Rare Pokemon, Near Mint",type:"FixedPrice",price:24.99,bids:0,watchers:2,end:h(240)},
      {item:"DEMO-1004",title:"1989 Upper Deck Star Rookie",type:"Auction",price:0.99,bids:0,watchers:1,end:h(52)},
      {item:"DEMO-1005",title:"2023 Bowman Chrome Auto /99",type:"Auction",price:31.00,bids:5,watchers:9,end:h(30)},
      {item:"DEMO-1006",title:"F1 Topps Chrome Refractor",type:"Auction",price:0.99,bids:0,watchers:0,end:h(70)},
      {item:"DEMO-1007",title:"1993 SP Foil Rookie",type:"Auction",price:6.50,bids:2,watchers:3,end:h(8)},
      {item:"DEMO-1008",title:"Vintage Wax Pack (Unopened)",type:"FixedPrice",price:39.99,bids:0,watchers:5,end:h(400)}
    ],
    sold: [
      {item:"DEMO-0901",title:"1996 Finest Refractor",price:42.00,date:h(-24)},
      {item:"DEMO-0902",title:"Team Lot, 25 cards",price:12.50,date:h(-72)},
      {item:"DEMO-0903",title:"PSA 9 Graded Rookie",price:88.00,date:h(-144)}
    ],
    orders: [
      {order:"DEMO-ORD-1",title:"1996 Finest Refractor",total:46.95,status:"paid"},
      {order:"DEMO-ORD-2",title:"Team Lot, 25 cards",total:17.45,status:"waiting payment"},
      {order:"DEMO-ORD-3",title:"PSA 9 Graded Rookie",total:92.95,status:"shipped"}
    ]
  };
})();
