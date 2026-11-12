var Result = (function () {
    function Result(phasergame) {
        this.rewardValue = 0;
		this.Giai_dac_biet = 0;
        this.Giai_phu_dac_biet_x = 0;
         this.Giai_nhat_x = 0;
         this.Giai_nhi_x = 0;
         this.Giai_ba_x = 0;
         this.Giai_tu_x = 0;
        this.Giai_nam_x = 0;
         this.Giai_sau_x = 0;
        this.trung_giai = "";
        this.gLocationsY = [117, 155, 201, 247, 287];
        this.beforeSpinStart = 500;
        this.delaySpinStart = 500;
        this.delayBallAppear = 250;
        this.delayBallStartMove = 250;
        this.timeBallMove = 500;
        this.delayBallDisappear = 500;
        this.bodyTestVRange = [];
        this.flagSpinCages = [false, false, false, false, false];
        this.game = phasergame;
		
    }
    //public render() {
    //    this.game.debug.pointer(this.game.input.activePointer);
    //}
    Result.prototype.init = function (param) {
		 this.rewardValue = 0;
		this.Giai_dac_biet = 0;
        this.Giai_phu_dac_biet_x = 0;
         this.Giai_nhat_x = 0;
         this.Giai_nhi_x = 0;
         this.Giai_ba_x = 0;
         this.Giai_tu_x = 0;
        this.Giai_nam_x = 0;
         this.Giai_sau_x = 0;
        this.trung_giai = "";
    };
    Result.prototype.preload = function () {
		
        this.game.stage.disableVisibilityChange = true;
    };
    Result.prototype.update = function () {
		
        for (var i = 0; i < 3; i++) {
            if (this.flagSpinCages[i]) {
                this.bodySpins[i].position[1] += 0.1;
                if (this.bodySpins[i].position[1] > this.bodyTestVRange[1]) {
                    this.bodySpins[i].position[1] = this.bodyTestVRange[0];
                }
            }
        }
    };
    Result.prototype.create = function () {
        var _this = this;
        this.ticketNames = ['A', 'B', 'C', 'D', 'E', 'G'];
        this.lstResultNumber = [];
        this.bodySpins = [];
        this.ticketPrize = 0;
        this.game.stage.backgroundColor = '#ffffff';
        var now = new Date();
        
        this.Giai_nhat_x = 0; 
        this.Giai_nhi_x = 0; 
        this.Giai_ba_x = 0;
        this.Giai_tu_x = 0;
        this.Giai_nam_x = 0;
        this.Giai_sau_x = 0;
        this.Giai_bay_x = 0;
        this.trung_giai = "";
        
         this.game.add.text(150, 20, 'Kết quả mở thưởng Max3D Pro ngày ' + now.getDate() + '/' + (now.getMonth() + 1) + '/' + now.getFullYear(), {
            font: "25px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
            wordWrapWidth: 900, align: "center", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
  
        this.game.add.image(0, 52, 'bangketqua');

        if (Global.tBaoType == -2) {
            this.TinhBaoNhieuBoSo(Global.AllTicket[0].tNumberString);
        }else if (Global.tBaoType == 2) {
            this.BaoBoSo = [];
            for (var i = 0; i < Global.AllTicket.length; i++) {
                this.TinhBaoBoSo(i);
            }
        } else if (Global.tBaoType > 3) {
            var tAllBoSo = [];
            for (var i = 0; i < Global.AllTicket.length; i++) {
                var tData = Global.AllTicket[i];
                if (tData.tNumberString != "")
                    tAllBoSo.push(tData.tNumberString);
                if (tData.tNumberString2 != "")
                    tAllBoSo.push(tData.tNumberString2);

            }

            this.TinhBaoNhieuBoSo(tAllBoSo);
        }


        this.createResult();
        this.calculatorTicket();
        this.createTextPrize();
        this.showTicket();
        this.createMachine();
        
        this.showFullScreenButton();
      
        
        this.game.time.events.add(this.beforeSpinStart, function () {
            _this.startSpin();
        });
        
    };
    
    Result.prototype.showFullScreenButton = function () {
        var _this = this;
        var btnFull = this.game.add.button(10, 10, 'full-screen', function () {
            if (!_this.game.scale.isFullScreen) {
                _this.game.scale.startFullScreen();
            }
            else {
                _this.game.scale.stopFullScreen();
            }
        });
        btnFull.scale.set(0.2, 0.2);
    };
   
    Result.prototype.createTextPrize = function () {
        this.txtPrizes = [];
        //let lstPrizeName = ['Giáº£i Nháº¥t', 'Giáº£i NhĂ¬', 'Giáº£i NhĂ¬', 'Giáº£i Ba', 'Giáº£i Ba', 'Giáº£i Ba', 'Giáº£i KK 1', 'Giáº£i KK 2'];
        //for (let i = 0; i < 6; i++) {
        //    let txtAlphabet = this.game.add.text(545, 95 + 40 * i, Resources.ticketNames[i], {
        //        font: "16px Arial", fill: "#da2888", wordWrap: true, fontWeight: 'bold',
        //        wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
        //    });
        //txtAlphabet.anchor.set(0, 0.5);
        //var border = this.game.add.sprite(570, txtAlphabet.y - 2, Resources.border.name);
        //border.anchor.set(0, 0.5);
        //    let txtNumber = this.game.add.text(570, txtAlphabet.y, '', {
        //        font: "16px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
        //        wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
        //    });
        //    txtNumber.anchor.set(0, 0.5);
        //    this.txtPrizes.push([txtAlphabet, txtNumber]);
        //}
    };
  
    Result.prototype.showTicket = function () {
       
        var bgTicket = this.game.add.image(693, 330, 'ticket');

        var bgLogo = this.game.add.image(bgTicket.x + 80, bgTicket.y + 10, 'logo-max3dpro-black');
        bgLogo.width = 70;
        bgLogo.height = 45;

        //loại chơi
        if (Global.tBaoType == -2) {
            this.game.add.text(bgLogo.left + 4, bgLogo.bottom + 5, 'BAO TỰ CHỌN', {
                font: "12px Arial", fill: "#000000", wordWrap: true,
                wordWrapWidth: 600, align: "right", boundsAlignH: 'center', boundsAlignV: 'middle'
            });
        }else if (Global.tBaoType == 2) {
            this.game.add.text(bgLogo.left + 4, bgLogo.bottom + 5, 'BAO BỘ SỐ', {
                font: "12px Arial", fill: "#000000", wordWrap: true,
                wordWrapWidth: 600, align: "right", boundsAlignH: 'center', boundsAlignV: 'middle'
            });
        }
        else if (Global.tBaoType > 2) {
            this.game.add.text(bgLogo.left + 20, bgLogo.bottom + 5, "BAO " + Global.tBaoType, {
                font: "12px Arial", fill: "#000000", wordWrap: true,
                wordWrapWidth: 600, align: "right", boundsAlignH: 'center', boundsAlignV: 'middle'
            });
          
        }


     //   var barcode = this.game.add.image(bgTicket.centerX, bgTicket.bottom - 30, 'barcode');
      //  barcode.anchor.set(0.5, 0.5);
        var txtGach = this.game.add.text(bgTicket.left + 20, bgTicket.top + 70, '---------------------------------------', {
            font: "16px Arial", fill: "#000000", wordWrap: true,
            wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        var txtGach2 = this.game.add.text(txtGach.left, bgTicket.top + 190, '---------------------------------------', {
            font: "16px Arial", fill: "#000000", wordWrap: true,
            wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        var txtSum = this.game.add.text(txtGach.left, txtGach2.bottom, 'Tổng', {
            font: "12px Arial", fill: "#000000", wordWrap: true,
            wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        var cost = this.numberWithCommas(this.ticketPrize);
        var txtCost = this.game.add.text(txtGach.right, txtSum.y, cost + 'VNĐ', {
            font: "12px Arial", fill: "#000000", wordWrap: true,
            wordWrapWidth: 600, align: "right", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        txtCost.anchor.set(1, 0);
        var txtKyQSMT = this.game.add.text(txtGach.left, txtSum.bottom - 3, 'Kỳ QSMT', {
            font: "12px Arial", fill: "#000000", wordWrap: true,
            wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        var dayName = ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"];
        var monName = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];
        var now = new Date();
        var today = dayName[now.getDay()] + " " + now.getDate() + "/" + monName[now.getMonth()] + "/" + now.getFullYear();
        var txtKy = this.game.add.text(txtGach.right, txtKyQSMT.y, '4321/'+now.getFullYear()+'\n' + today + '\n1234 - ABCD', {
            font: "12px Arial", fill: "#000000", wordWrap: true,
            wordWrapWidth: 600, align: "right", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        txtKy.lineSpacing = -7;
        txtKy.anchor.set(1, 0);
        this.txtTickets = [];
        var tCount = 0;
     

      
        if (Global.tBaoType != -2) {
            if (Global.tBaoType > 2) {
                var txtNameTicket = this.game.add.text(txtGach.left + 10, txtGach.bottom - 5 + 18 * tCount, 'A:  ', {
                    font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                    wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                });

                var x = txtNameTicket.x + 20;
                var y = txtNameTicket.y;

                var numberArrayCount = [];
                for (var i = 0; i < Global.AllTicket.length; i++) {
                    var numberArray = [];
                    var tData = Global.AllTicket[i];
                    if (tData.tAmount != 0) {
                        if (tData.tNumberString.length == 3) {
                            var txtNumberOne = this.game.add.text(x, y, tData.tNumberString, {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });

                            numberArray.push(txtNumberOne);
                            numberArrayCount.push(txtNumberOne);

                            x += 40;
                        }
                        if (tData.tNumberString2.length == 3) {
                            var txtchamphay = this.game.add.text(x, y, '  ', {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });

                            var txtNumber2 = this.game.add.text(x, y, tData.tNumberString2, {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });
                            numberArray.push(txtNumber2);
                            numberArrayCount.push(txtNumber2);
                            x += 40;
                        }

                        this.txtTickets.push(numberArray);

                        if (numberArrayCount.length % 4 == 0) {
                            x = txtNameTicket.x + 20;
                            y += 20;
                        }
                    }
                }



            } else {
                for (var i = 0; i < Global.AllTicket.length; i++) {
                    var numberArray = [];
                    var tData = Global.AllTicket[i];

                    if (tData.tAmount != 0) {
                        if (tData.tNumberString.length == 3) {
                            var txtNameTicket = this.game.add.text(txtGach.left + 10, txtGach.bottom - 5 + 18 * tCount, tData.tAmount == 0 ? '' : tData.tName + ':  ', {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });

                            var txtNumberOne = this.game.add.text(txtNameTicket.x + 20, txtNameTicket.y, tData.tNumberString, {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });

                            numberArray.push(txtNumberOne);
                        }

                        if (tData.tNumberString2.length == 3) {

                            var txtchamphay = this.game.add.text(txtNumberOne.x + 25, txtNumberOne.y, '  ', {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });

                            var txtNumber2 = this.game.add.text(txtchamphay.x + 10, txtchamphay.y, tData.tNumberString2, {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });
                            numberArray.push(txtNumber2);

                        }

                        this.txtTickets.push(numberArray);

                        if (tData.tTC == "1") {
                            //add tự chọn
                            var tc_left = txtNumberOne.x + 115;
                            this.game.add.text(tc_left, txtNameTicket.y, "TC", {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 100, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });

                        }
                        //add amout

                        if (Global.tBaoType == -1) {
                            var txtAmount = this.game.add.text(txtGach.right - 10, txtNumberOne.y, tData.tAmountString, {
                                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                            });
                            txtAmount.anchor.set(1, 0);
                        }
                        if (tData.tAmount != 0)
                            tCount++;

                    }

                }

            }


        } else {
            var txtNameTicket = this.game.add.text(txtGach.left + 10, txtGach.bottom - 5 + 18 * tCount, '', {
                font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
            });

            var x = txtNameTicket.x + 20;
            var y = txtNameTicket.y;
            console.log(Global.AllTicket[0]);
            for (var i = 0; i < Global.AllTicket[0].tNumberString.length; i++) {
                console.log(Global.AllTicket[0]);
                var txtNumberOne = this.game.add.text(x, y, Global.AllTicket[0].tNumberString[i], {
                    font: "12px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                    wordWrapWidth: 600, align: "left", boundsAlignH: 'center', boundsAlignV: 'middle'
                });
                x += 40;

                if (i > 0 && (i+1) % 4 == 0) {
                    x = txtNameTicket.x + 20;
                    y += 20;
                }

            }
        

        }

       

    };

    Result.prototype.TinhBaoNhieuBoSo = function (tAllBoSo) {
        this.BaoNhieuBoSo = [];
        for (var i = 0; i < tAllBoSo.length; i++) {
            for (var j = 0; j < tAllBoSo.length; j++) {
                if (tAllBoSo[i] != tAllBoSo[j]) {
                    this.BaoNhieuBoSo.push([tAllBoSo[i], tAllBoSo[j]]);
                }
            }
        }

        console.log(this.BaoNhieuBoSo);

    }

    Result.prototype.TinhBaoBoSo = function (tIndex) {
        var tData = Global.AllTicket[tIndex];
        var BoSos = [];
        //chơi bao bộ số
        if (tData.tNumber.length > 0) {
            var arr1 = permutator(tData.tNumber.slice(0, 3));
            var arr2 = permutator(tData.tNumber.slice(3, 6));
            for (var i = 0; i < arr1.length; i++) {
                for (var j = 0; j < arr2.length; j++) {
                    let item = [];
                    item.push(arr1[i]);
                    item.push(arr2[j]);
                    BoSos.push(item);
                }
            }
        }

        this.BaoBoSo.push({
            tName: tData.tName,
            tIndex: tData.tIndex,
            tBoSo: BoSos,
            tAmout: tData.tAmount
        })

    }
  Result.prototype.showReward = function () {
        var _this = this;
      
        this.calculatorResult();
        var txtWin = this.game.add.text(545, 370, '', {
            font: "22px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
            wordWrapWidth: 600, align: "center", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        txtWin.anchor.set(0.5, 0.5);
        var txtWin2 = this.game.add.text(txtWin.centerX, 435, '', {
            font: "18px Arial", fill: "#000000", wordWrap: true,
            wordWrapWidth: 270, align: "center", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        txtWin2.anchor.set(0.5, 0.5);
        var txtPrice = this.game.add.text(txtWin.centerX, 510, '', {
            font: "26px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
            wordWrapWidth: 500, align: "center", boundsAlignH: 'center', boundsAlignV: 'middle'
        });
        txtPrice.anchor.set(0.5, 0.5);
        var btnPlayAgain = this.game.add.button(txtWin.centerX + 10, txtPrice.y + 50, 'play-again', function () {
            _this.game.state.start('intro', true, 'State1');
        });
        btnPlayAgain.scale.set(0.7, 0.7);
        btnPlayAgain.anchor.set(0.5, 0.5);
        btnPlayAgain.onInputDown.add(function () {
            btnPlayAgain.scale.set(0.5, 0.5);
        }, this);
        btnPlayAgain.onInputUp.add(function () {
            btnPlayAgain.scale.set(0.7, 0.7);
        }, this);
        if (this.rewardValue > 0) {
        	this.trung_giai = "";
            if (this.Giai_dac_biet > 0) this.trung_giai += this.Giai_dac_biet + " lần giải đặc biệt, ";
            if (this.Giai_phu_dac_biet_x > 0) this.trung_giai += this.Giai_phu_dac_biet_x + " lần giải phụ đặc biệt, ";
            //Giai_phu_dac_biet_x
        		if(this.Giai_nhat_x > 0) this.trung_giai += this.Giai_nhat_x + " lần giải nhất, ";
            	if(this.Giai_nhi_x > 0) this.trung_giai += this.Giai_nhi_x + " lần giải nhì, ";
            	if(this.Giai_ba_x > 0) this.trung_giai += this.Giai_ba_x + " lần giải ba, ";
            	if(this.Giai_tu_x > 0) this.trung_giai += this.Giai_tu_x + " lần giải tư, ";
            	if(this.Giai_nam_x > 0) this.trung_giai += this.Giai_nam_x + " lần giải năm, ";
            	if(this.Giai_sau_x > 0) this.trung_giai += this.Giai_sau_x + " lần giải sáu   ";
        	//}
        	
        	
        if(this.trung_giai.length > 2)	this.trung_giai = this.trung_giai.substring(0, this.trung_giai.length - 2);
        	
            txtWin.text = 'Chúc mừng!!!';
           // console.log(this.trung_giai);
            txtWin2.text = 'Bạn đã trúng thưởng '+ 	this.trung_giai;
          //  txtWin2.text = 'Bạn đã trúng thưởng 1 lan giai phu dac biet, 1 lan giai nhat, 1 lan giai ba, 3 lan giai tu, 2 lan giai nam, 4 lan giai 6';
            txtPrice.text = this.numberWithCommas(this.rewardValue) + ' VNĐ';
        }
        else {
            txtWin.text = 'Chưa trúng thưởng!';
            txtWin2.text = 'Chúc bạn may mắn lần sau!';
        }
    };
    
    
    Result.prototype.createMachine = function () {
        var msl = { x: 20, y: 370 };
        var mdV = 150;
        for (var i = 0; i < 3; i++) {
            this.game.add.image(msl.x + i * mdV, msl.y, 'cage_max3d');
        }
        this.game.physics.startSystem(Phaser.Physics.P2JS);
        this.game.physics.p2.restitution = 0.9;
        this.game.physics.p2.gravity.y = 300;
        var sim = this.game.physics.p2;
        this.bodyTestVRange = [sim.pxmi(580), sim.pxmi(470)];
        this.bodySpins = [];
        for (var i = 0; i < 3; i++) {
            var rootPoint = { x: 78 + mdV * i, y: 490 };
            this.createMachineBody(rootPoint, i);
        }
    };
    
    Result.prototype.createMachineBody = function (rootPoint, index) {
        var sim = this.game.physics.p2;
      //  var points = [[-34, 0], [34, 0], [0, -60], [0, 60]];
      //  var angles = [];
        var option = {};
        option.position = [sim.pxmi(rootPoint.x), sim.pxmi(rootPoint.y)];
        option.angle = 0;
        var body = new p2.Body(option); //w:68 h:138 
        //body.addShape(new p2.Rectangle(sim.pxmi(100), sim.pxmi(100)), [0, 0]);
        body.addShape(new p2.Rectangle(sim.pxmi(30), sim.pxmi(140)), [sim.pxmi(-47), 0]);
        body.addShape(new p2.Rectangle(sim.pxmi(30), sim.pxmi(140)), [sim.pxmi(49), 0]);
        body.addShape(new p2.Rectangle(sim.pxmi(60), sim.pxmi(30)), [0, sim.pxmi(83)]);
        body.addShape(new p2.Rectangle(sim.pxmi(60), sim.pxmi(30)), [0, sim.pxmi(-83)]);
        body.addShape(new p2.Rectangle(sim.pxmi(20), sim.pxmi(30)), [sim.pxmi(-32), sim.pxmi(-66)], Math.PI / 4); //   /
        body.addShape(new p2.Rectangle(sim.pxmi(20), sim.pxmi(30)), [sim.pxmi(32), sim.pxmi(66)], Math.PI / 4); //   /
        body.addShape(new p2.Rectangle(sim.pxmi(20), sim.pxmi(30)), [sim.pxmi(-32), sim.pxmi(66)], 3 * Math.PI / 4); //   \
        body.addShape(new p2.Rectangle(sim.pxmi(20), sim.pxmi(30)), [sim.pxmi(32), sim.pxmi(-66)], 3 * Math.PI / 4); //   \
        sim.world.addBody(body);
        var bounds = new Phaser.Rectangle(rootPoint.x - 30, rootPoint.y - 30, 60, 60);
        this.balls = [];
        var ballRadius = 6;
      /*  if (19 == index) {
            for (var i = 0; i < 6; i++) {
                var ball = this.game.add.sprite(0, 0, 'ball-' + this.ticketNames[i].toLowerCase());
                ball.x = bounds.randomX;
                ball.y = bounds.randomY;
                ball.scale.set(ballRadius * 2 / ball.width, ballRadius * 2 / ball.width);
                this.game.physics.p2.enable(ball, true);
                ball.body.clearShapes();
                ball.body.setCircle(ballRadius);
                this.balls.push(ball.body);
            }
        }
        else {*/
            for (var i = 0; i < 9; i++) {
                var ball = this.game.add.sprite(0, 0, (index + 1) + '-ball-' + i);
                ball.x = bounds.randomX;
                ball.y = bounds.randomY;
                ball.scale.set(12 / 167, 12 / 167);
                this.game.physics.p2.enable(ball, true);
                ball.body.setCircle(ballRadius);
                this.balls.push(ball.body);
            }
       // }
        var option2 = {};
        option2.position = [sim.pxmi(rootPoint.x), sim.pxmi(580)];
        option2.angle = 0;
        var bodyTest = new p2.Body(option2);
        bodyTest.addShape(new p2.Rectangle(sim.pxmi(30), sim.pxmi(30)));
        sim.world.addBody(bodyTest);
        this.bodySpins.push(bodyTest);
       
    };
   
    Result.prototype.click = function (pointer) {
        var bodies = this.game.physics.p2.hitTest(pointer.position, this.balls);
        if (bodies.length) {
            //  Attach to the first body the mouse hit
            this.mouseSpring = this.game.physics.p2.createSpring(this.mouseBody, bodies[0], 0, 30, 1);
        }
    };
    Result.prototype.release = function () {
        this.game.physics.p2.removeSpring(this.mouseSpring);
    };
    Result.prototype.move = function (pointer, x, y, isDown) {
        this.mouseBody.body.x = x;
        this.mouseBody.body.y = y;
    };

    Result.prototype.createResult = function () {
        this.lstResultNumber = [];
        this.lstResultNumberString = [];

        //this.lstResultNumber.push([1, 2, 3]);
        //this.lstResultNumber.push([1, 2, 2]);
        //this.lstResultNumber.push([2, 3, 5]);
        //this.lstResultNumber.push([2, 3, 6]);
        //this.lstResultNumber.push([3, 5, 8]);
        //this.lstResultNumber.push([5, 8, 9]);

        //this.lstResultNumber.push([6, 7, 8]);
        //this.lstResultNumber.push([6, 7, 9]);
        //this.lstResultNumber.push([7, 8, 9]);
        //this.lstResultNumber.push([7, 9, 1]);
        //this.lstResultNumber.push([8, 6, 5]);
        //this.lstResultNumber.push([8, 6, 4]);

        //this.lstResultNumber.push([9, 1, 2]);
        //this.lstResultNumber.push([3, 4, 9]);
        //this.lstResultNumber.push([4, 7, 8]);
        //this.lstResultNumber.push([5, 3, 4]);
        //this.lstResultNumber.push([5, 6, 7]);
        //this.lstResultNumber.push([5, 2, 1]);
        //this.lstResultNumber.push([1, 6, 7]);
        //this.lstResultNumber.push([1, 8, 9]);


        //this.lstResultNumberString.push("123");
        //this.lstResultNumberString.push("122");
        //this.lstResultNumberString.push("235");
        //this.lstResultNumberString.push("236");
        //this.lstResultNumberString.push("358");
        //this.lstResultNumberString.push("589");

        //this.lstResultNumberString.push("678");
        //this.lstResultNumberString.push("679");
        //this.lstResultNumberString.push("789");
        //this.lstResultNumberString.push("791");
        //this.lstResultNumberString.push("865");
        //this.lstResultNumberString.push("864");

        //this.lstResultNumberString.push("912");
        //this.lstResultNumberString.push("349");
        //this.lstResultNumberString.push("478");
        //this.lstResultNumberString.push("534");
        //this.lstResultNumberString.push("567");
        //this.lstResultNumberString.push("521");
        //this.lstResultNumberString.push("167");
        //this.lstResultNumberString.push("189");






        var count = 0;
        var rdIndex = Math.floor(Math.random() * 4);
        var rdToIndex = Math.floor(Math.random() * 19);
        var max = 20;
        //  if(Global.tGameType == 0) max = 20;
        //   else max = 10;
        var checked = false;

        while (count < max) {
            var newNumber = [];

            if (count == rdToIndex && Global.AllTicket[rdIndex].tNumberString != '') {
                newNumber = Global.AllTicket[rdIndex].tNumberString;
                checked = true;
            }
            else {
                newNumber = this.generateRandomNumber(3);
            }


            var newNumberStr = '';
            for (var _i = 0, newNumber_1 = newNumber; _i < newNumber_1.length; _i++) {
                var n = newNumber_1[_i];
                newNumberStr += n;
            }
            var flag = false;
            //có trong mảng rồi thì bỏ qua
            for (var _a = 0, _b = this.lstResultNumberString; _a < _b.length; _a++) {
                var str = _b[_a];
                if (newNumberStr == str) {
                    flag = true;
                    break;
                }
            }




            if (!flag) {
                count++;
                // console.log("newnumber tren: "+ newNumber);
                this.lstResultNumber.push(newNumber);
                this.lstResultNumberString.push(newNumberStr);
            }


            if (!checked && count + 1 == max) {
                var random_ = Math.floor(Math.random() * 17);
                var nb = '';
                if (Global.AllTicket[0].tNumberString != '') {
                    nb = Global.AllTicket[0].tNumberString;
                } else if (Global.AllTicket[1].tNumberString != '') {
                    nb = Global.AllTicket[1].tNumberString;
                } else if (Global.AllTicket[2].tNumberString != '') {
                    nb = Global.AllTicket[2].tNumberString;
                } else if (Global.AllTicket[3].tNumberString != '') {
                    nb = Global.AllTicket[3].tNumberString;
                }
                var new_nbstr = '';
                for (var _i = 0, newNumber_1 = nb; _i < newNumber_1.length; _i++) {
                    var n = newNumber_1[_i];
                    new_nbstr += n;
                }

                this.lstResultNumber[random_] = nb;
                this.lstResultNumberString[random_] = new_nbstr;

            }

        }

        console.log(this.lstResultNumber);
        console.log(this.lstResultNumberString);

        if (Global.tGameType == 1) {


            var random_ = Math.floor(Math.random() * 10);
            var nb = '';
            if (Global.AllTicket[0].tNumberString2 != '') {
                nb = Global.AllTicket[0].tNumberString2;
            } else if (Global.AllTicket[1].tNumberString2 != '') {
                nb = Global.AllTicket[1].tNumberString2;
            } else if (Global.AllTicket[2].tNumberString2 != '') {
                nb = Global.AllTicket[2].tNumberString2;
            } else if (Global.AllTicket[3].tNumberString2 != '') {
                nb = Global.AllTicket[3].tNumberString2;
            }
            var new_nbstr = '';
            for (var _i = 0, newNumber_1 = nb; _i < newNumber_1.length; _i++) {
                var n = newNumber_1[_i];
                new_nbstr += n;
            }

            this.lstResultNumber[random_] = nb;
            this.lstResultNumberString[random_] = new_nbstr;

        }


    };


    Result.prototype.startSpin = function () {
        var _this = this;
        this.flagSpinCages = [true, true, true, true, false];
        this.game.time.events.add(this.delaySpinStart, function () {
            _this.startSpinNumber();
        });
    };
  
    Result.prototype.startSpinNumber = function () {
        var _this = this;
        this.lstResultBall = [];
        var count = 19;
        var callback = function () {
            
        	if (count > 0) {
            }
        	
        	//console.log("count spinnumber: "+ count);
            if (count < 0) {
                _this.flagSpinCages = [false, false, false, false, true];
                for (var _i = 0, _a = _this.bodySpins; _i < _a.length; _i++) {
                    var b = _a[_i];
                    b.position[1] = _this.bodyTestVRange[0];
                }
               // _this.startSpinAlphabet();
                
                _this.showReward();
                return;
            }
           // console.log("spiner number: "+ _this.lstResultNumber[count]);
            _this.animateANumber(_this.lstResultNumber[count], callback, count);
            count--;
        };
        
        callback();
    };
    
    Result.prototype.animateANumber = function (arr, onComplete, numberCount) {
        var _this = this;
      //  console.log("arr: " + arr.length);
        if (arr.length != 3) {
            console.error('length of number must equal 3');
            return;
       }
        
        var balls = [];
        this.lstResultBall.push(balls);
        var endWidth = 20;
        var count = 0;
        var loop = this.game.time.events.loop(this.delayBallAppear, function () {
            var index = count;
            
           // console.log("arr: "+ arr + ", count: "+ count);
            var ball = _this.game.add.image(80 + 149 * count, 510, (count + 1) + '-ball-' + arr[count]);
            ball.anchor.set(0.5, 0.5);
            ball.scale.set(12 / 167, 12 / 167);
            ball.data = arr[count];
            balls.push(ball);
            var tween = _this.game.add.tween(ball).to({ y: 410 }, _this.timeBallMove, Phaser.Easing.Elastic.Out, true, _this.delayBallStartMove);
            tween.onComplete.add(function () {
                _this.game.add.tween(ball.scale).to({ x: 40 / 167, y: 40 / 167 }, 500, Phaser.Easing.Linear.None, true, 500);
                _this.game.add.tween(ball).to({ y: 360 }, 500, Phaser.Easing.Linear.None, true, 500)
                    .onComplete.add(function () {
                    if (numberCount == 3) {
                        _this.flagSpinCages[index] = false;
                    }
                    
                    if (index == 2) {
                        _this.game.time.events.add(_this.delayBallDisappear, function () {
                        	
                        	var endX = 0;
                            var endY = 97;
                            switch(numberCount) {
                            case 0: 
                            	endX = 393;
                            	break;
                            case 1: 
                            	endX = 516;
                            	break;
                            case 2: 
                            	 endY = 149;
                            	 endX = 267;
                            	break;
                            case 3: 
                            	 endY = 149;
                            	 endX =  390;
                            	break;
                            	
                            case 4: 
                            	 endY = 149;
                            	 endX = 516;
                            	break;
                            case 5: 
                            	 endY = 149;
                            	 endX = 643;
                            	break;
                            case 6:
                            	endY = 202;
                           		endX = 143;
                            	break;
                            case 7: 
                            	endY = 202;
                           		endX = 267;
                            	break;
                            case 8: 
                            	endY = 202;
                           		endX = 393 ;
                            	break;
                            case 9: 
                            	endY = 202;
                           		endX = 522;
                            	break;
                            case 10: 
                            	endY = 202;
                           		endX = 640;
                            	break;
                            case 11: 
                            	endY = 202;
                           		endX = 765;
                            	break;
                            case 12: 
                            	endX = 266;
                            	endY = 255;
                            	break;
                            case 13: 
                            	endY = 255;
                            	endX = 392;
                            	break;
                            case 14: 
                            	endY = 255;
                            	endX = 518;
                            	break;
                            case 15: 
                            	endX = 645;
                            	endY = 255;
                            	break;
                            case 16: 
                            	endX = 266;
                            	endY = 305;
                            	break;
                            case 17: 
                            	endX = 390;
                            	endY = 305;
                            	break;
                            case 18: 
                            	endX = 517;
                            	endY = 305;
                            	break;
                            case 19: 
                            	endX = 643;
                            	endY = 305;
                            	break;
                            }
                    		
                    		
                            for (var i = 0; i < 3; i++) {	
                            	endX += endWidth + 14;
	
                                _this.game.add.tween(balls[i].scale).to({ x: endWidth / 100, y: endWidth / 100 }, 200, Phaser.Easing.Linear.None, true, 200);
                                _this.game.add.tween(balls[i]).to({ x: endX, y: endY }, 200, Phaser.Easing.Linear.None, true, 200);
                            }
                            if (onComplete != undefined && onComplete != null) {
                                onComplete();
                            }
                        });
                    } 
                    
                });
            }, _this, 0.5);
            
            count++;
            
            if (count == 3) {
                _this.game.time.events.remove(loop);
            }
        });
    };
    
    Result.prototype.startSpinAlphabet = function () {
        var _this = this;
        var count = 0;
        var onComplete = function () {
        	//var g1 = _this.lstResultNumber[_this.lstResultAlphabet[2]];
            //this.txtPrizes[6][1].text = 'x' + g1[1] + g1[2] + g1[3];
            //this.txtPrizes[6][2].text = Resources.prizeNames[PrizeType.GKK1];
            //this.txtPrizes[7][1].text = 'xx' + g1[2] + g1[3];
            //this.txtPrizes[7][2].text = Resources.prizeNames[PrizeType.GKK2];
            _this.orderResultTable();
            _this.flagSpinCages = [false, false, false, false, false];
            for (var _i = 0, _a = _this.bodySpins; _i < _a.length; _i++) {
                var b = _a[_i];
                b.position[1] = _this.bodyTestVRange[1];
            }
        };
        var loop = this.game.time.events.loop(3000, function () {
            var index = count;
            var ball = _this.game.add.image(608, 510, 'ball-' + _this.ticketNames[_this.lstResultAlphabet[index]].toLowerCase());
            ball.anchor.set(0.5, 0.5);
            ball.scale.set(12 / 167, 12 / 167);
            var tween = _this.game.add.tween(ball).to({ y: 410 }, _this.timeBallMove, Phaser.Easing.Elastic.Out, true, 0);
            tween.onComplete.add(function () {
                _this.game.add.tween(ball.scale).to({ x: 40 / 167, y: 40 / 167 }, 500, Phaser.Easing.Linear.None, true, 500);
                _this.game.add.tween(ball).to({ y: 360 }, 500, Phaser.Easing.Linear.None, true, 500)
                    .onComplete.add(function () {
                    if (index == 2) {
                        _this.showBallG1();
                    }
                    else {
                        _this.showBallG2(index);
                    }
                    _this.game.time.events.add(_this.delayBallDisappear, function () {
                        ball.destroy();
                        //this.txtPrizes[this.lstResultAlphabet[index]][2].text = Resources.prizeNames[Resources.prizeSpinOrder[index]];
                        if (index == 2) {
                            onComplete();
                        }
                    });
                });
            }, _this, 1);
            
            count++;
            if (count == 3) {
                _this.game.time.events.remove(loop);
            }
        });
    };
   
    Result.prototype.orderResultTable = function () {
        //let lstY: number[] = [];
        //lstY.push(this.txtPrizes[0][0].y);
        //lstY.push(this.txtPrizes[1][0].y);
        //lstY.push(this.txtPrizes[2][0].y);
        //lstY.push(this.txtPrizes[3][0].y);
        //lstY.push(this.txtPrizes[4][0].y);
        //lstY.push(this.txtPrizes[5][0].y);
        //let lstLocationY: number[] = [0, 0, 0, 0, 0, 0];
        //lstLocationY[this.lstResultAlphabet[2]] = lstY[0];
        //lstLocationY[this.lstResultAlphabet[0]] = lstY[1];
        //lstLocationY[this.lstResultAlphabet[1]] = lstY[2];
        //lstLocationY[this.lstResultAlphabet[3]] = lstY[3];
        //lstLocationY[this.lstResultAlphabet[4]] = lstY[4];
        //lstLocationY[this.lstResultAlphabet[5]] = lstY[5];
        for (var i = 0; i < 6; i++) {
            //var ind = i;
        }
        this.showBallResult();
    };
 
  
    Result.prototype.showTextResult = function () {
        for (var _i = 0, _a = this.lstResultBall; _i < _a.length; _i++) {
            var balls = _a[_i];
            for (var _b = 0, balls_1 = balls; _b < balls_1.length; _b++) {
                var ball = balls_1[_b];
                this.game.add.text(ball.x - 6, ball.y - 13, ball.data, {
                    font: "50px Arial", fill: "#000000", wordWrap: true, fontWeight: 'bold',
                    wordWrapWidth: 900, align: "center", boundsAlignH: 'center', boundsAlignV: 'middle'
                }).scale.set(0.5, 0.5);
                ball.destroy();
            }
        }
    };
  
    Result.prototype.getIndicesOf = function (searchStr, str, caseSensitive) {
        var startIndex = 0, searchStrLen = searchStr.length;
        var index, indices = [];
        if (!caseSensitive) {
            str = str.toLowerCase();
            searchStr = searchStr.toLowerCase();
        }
        while ((index = str.indexOf(searchStr, startIndex)) > -1) {
            indices.push(index);
            startIndex = index + searchStrLen;
        }
        return indices;
    };

    Result.prototype.calculatorTicket = function () {
        var tAmounts = 0;
        if (Global.tBaoType == -1) {
            for (var i = 0; i < 4; i++) {
                tAmounts += Global.AllTicket[i].tAmount;
            }
           
        } 
        if (Global.tBaoType == 2) {
            for (var i = 0; i < this.BaoBoSo.length; i++) {
                var dongia = this.BaoBoSo[i].tAmout;
                tAmounts += this.BaoBoSo[i].tBoSo.length * dongia;
            }
        }

        if (Global.tBaoType > 2) {
            switch (Global.tBaoType) {
                case 3:
                    tAmounts = 10000 * 6;
                    break;
                case 4:
                    tAmounts = 10000 * 12;
                    break;
                case 5:
                    tAmounts = 10000 * 20;
                    break;
                case 6:
                    tAmounts = 10000 * 30;
                    break;
                case 7:
                    tAmounts = 10000 * 42;
                    break;
                case 8:
                    tAmounts = 10000 * 56;
                    break;
            }
        }

        if (Global.tBaoType == -2) { //bao tự chọn
            switch (Global.AllTicket[0].tNumberString.length) {
                case 3:
                    tAmounts = 10000 * 6;
                    break;
                case 4:
                    tAmounts = 10000 * 12;
                    break;
                case 5:
                    tAmounts = 10000 * 20;
                    break;
                case 6:
                    tAmounts = 10000 * 30;
                    break;
                case 7:
                    tAmounts = 10000 * 42;
                    break;
                case 8:
                    tAmounts = 10000 * 56;
                case 9:
                    tAmounts = 10000 * 72;
                    break;
                case 10:
                    tAmounts = 10000 * 90;
                    break;
                case 11:
                    tAmounts = 10000 * 110;
                    break;
                case 12:
                    tAmounts = 10000 * 132;
                    break;
                case 13:
                    tAmounts = 10000 * 156;
                    break;
                case 14:
                    tAmounts = 10000 * 182;
                case 15:
                    tAmounts = 10000 * 210;
                case 16:
                    tAmounts = 10000 * 240;
                case 17:
                    tAmounts = 10000 * 272;
                case 18:
                    tAmounts = 10000 * 306;
                case 19:
                    tAmounts = 10000 * 342;
                case 20:
                    tAmounts = 10000 * 380;
                    break;
            }
        }

        this.ticketPrize = tAmounts;


        return tAmounts;
    };
   
   
    Result.prototype.calculatorResult = function () {

        console.log("ket qua:", this.lstResultNumberString);
        var reward = 0;
        var type = 1; 

        if (Global.tBaoType == -1) { //chơi thường

            for (var _i = 0, _a = Global.AllTicket; _i < _a.length; _i++) {
                var ticket = _a[_i];
                if (ticket.tNumberString == '')
                    continue;

                var result = 0;
                result += this.getPrize3D3D_GiaiDacBiet(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);

                result += this.getPrize3D3D_GiaiPhuDacBiet(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);

                result += this.getPrize3D3D_GiaiNhat(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);

                result += this.getPrize3D3D_GiaiNhi(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);

                result += this.getPrize3D3D_GiaiBa(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);

                result += this.getPrize3D3D_GiaiTu(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);

                result += this.getPrize3D3D_GiaiNam(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);

                result += this.getPrize3D3D_GiaiSau(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);
                //  console.log("giari6: "+ result);
           //     result += this.getPrize3D3D_GiaiBay(_i, ticket.tNumberString, ticket.tNumberString2, ticket.tAmount);
                //    console.log("giari7: "+ result);
                reward += result;

                

            }//end for global

        }
        if (Global.tBaoType == 2) { //chơi bao bộ số
            console.log("bao bộ số")
            /*
              {tName: "A", tIndex: 0, tBoSo: Array(36), tAmout: 10000}
              {tName: "B", tIndex: 1, tBoSo: Array(36), tAmout: 10000}
              {tName: "C", tIndex: 2, tBoSo: Array(18), tAmout: 10000}
              {tName: "D", tIndex: 3, tBoSo: Array(18), tAmout: 10000}

             */
            for (var i = 0; i < this.BaoBoSo.length; i++) {
                var item = this.BaoBoSo[i];
                var result = 0;
                if (item.tAmout != 0 & item.tBoSo.length > 0) {
                    for (var j = 0; j < item.tBoSo.length; j++) {
                       // console.log(item.tBoSo[j]);
                        result += this.getPrize3D3D_GiaiDacBiet(i, item.tBoSo[j][0], item.tBoSo[j][1], item.tAmout);

                        result += this.getPrize3D3D_GiaiPhuDacBiet(i, item.tBoSo[j][0], item.tBoSo[j][1], item.tAmout);

                        result += this.getPrize3D3D_GiaiNhat(i, item.tBoSo[j][0], item.tBoSo[j][1], item.tAmout);
                       
                        result += this.getPrize3D3D_GiaiNhi(i, item.tBoSo[j][0], item.tBoSo[j][1], item.tAmout);
                     
                        result += this.getPrize3D3D_GiaiBa(i, item.tBoSo[j][0], item.tBoSo[j][1], item.tAmout);
                      
                        result += this.getPrize3D3D_GiaiTu(i, item.tBoSo[j][0], item.tBoSo[j][1], item.tAmout);
                       
                        result += this.getPrize3D3D_GiaiNam(i, item.tBoSo[j][0], item.tBoSo[j][1], item.tAmout);    
                       
                        result += this.getPrize3D3D_GiaiSau(i, item.tBoSo[j][0], item.tBoSo[j][1], item.tAmout);
                       
                     
                       

                    }
                    console.log("tien thuong:",result);
                    reward += result;

                } else continue;
            }
        }//end type 2

        if (Global.tBaoType > 3 || Global.tBaoType == -2) {
            let tAmout = 10000;
            for (var i = 0; i < this.BaoNhieuBoSo.length; i++) {
                var item = this.BaoNhieuBoSo[i];
                var result = 0;
                result += this.getPrize3D3D_GiaiDacBiet(i, item[0], item[1], tAmout);

                result += this.getPrize3D3D_GiaiPhuDacBiet(i, item[0], item[1], tAmout);

                result += this.getPrize3D3D_GiaiNhat(i, item[0], item[1], tAmout);

                result += this.getPrize3D3D_GiaiNhi(i, item[0], item[1], tAmout);

                result += this.getPrize3D3D_GiaiBa(i, item[0], item[1], tAmout);

                result += this.getPrize3D3D_GiaiTu(i, item[0], item[1], tAmout);

                result += this.getPrize3D3D_GiaiNam(i, item[0], item[1], tAmout);

                result += this.getPrize3D3D_GiaiSau(i, item[0], item[1], tAmout);

              

                reward += result;

            }

        }

     

        this.rewardValue = reward;
    
    };

     Result.prototype.getPrize3D3D_GiaiDacBiet = function (index, number1, number2, amout) {
        var prize = 0;
        var x = amout / 10000;
        var result = this.lstResultNumberString;
            if (result[0] == number1 && result[1] == number2) {
                prize = 2000000000 * x;
                if (Global.tBaoType < 3 && Global.tBaoType != -2) {
                    this.txtTickets[index][0].addColor('#da2888', 0);
                    this.txtTickets[index][1].addColor('#da2888', 0);
                }
                this.Giai_dac_biet = 1;
            }
    

        return prize;
    }

    Result.prototype.getPrize3D3D_GiaiPhuDacBiet = function(index, number1, number2, amout) {
    	var prize = 0;
    	var x = amout/10000;
        var result = this.lstResultNumberString;
       
            if (result[0] == number2 && result[1] == number1) {
                prize = 400000000 * x;
                if (Global.tBaoType < 3 && Global.tBaoType != -2) {
                    this.txtTickets[index][0].addColor('#da2888', 0);
                    this.txtTickets[index][1].addColor('#da2888', 0);
                }
                this.Giai_phu_dac_biet_x = 1;
            }
        

         return prize;
    };

    Result.prototype.getPrize3D3D_GiaiNhat = function(index,number1, number2, amout) {
    	var check1 = false, check2 = false;
    	var x = amout/10000;
        var prize = 0;
        var result = this.lstResultNumberString;
       
            for (var i = 2; i < 6; i++) {
                if (result[i] == number1 & !check1)
                    check1 = true;
                else if (result[i] == number2)
                    check2 = true;
            }

        if (check1 & check2) {
            if (Global.tBaoType < 3 && Global.tBaoType != -2) {
                this.txtTickets[index][0].addColor('#da2888', 0);
                this.txtTickets[index][1].addColor('#da2888', 0);
            }
                prize = 30000000 * x;
                //this.trung_giai += "giải nhì, ";
                this.Giai_nhat_x++;

                if (number1 == number2) {
                    prize = prize * 2;
                    this.Giai_nhat_x++;
                }
            }

      
    	return prize;
    };
    
    Result.prototype.getPrize3D3D_GiaiNhi = function(index,number1, number2, amout) {
    	var check1 = false, check2 = false;
    	var x = amout/10000;
        var prize = 0;
        var result = this.lstResultNumberString;
       
            for (var i = 6; i < 12; i++) {
                if (result[i] == number1 & !check1) check1 = true;
                else if (result[i] == number2) check2 = true;
            }

        if (check1 & check2) {
            if (Global.tBaoType < 3 && Global.tBaoType != -2) {
                this.txtTickets[index][0].addColor('#da2888', 0);
                this.txtTickets[index][1].addColor('#da2888', 0);
            }
                prize = 10000000 * x;
                //this.trung_giai += "giải ba, ";
                this.Giai_nhi_x++;

                if (number1 == number2) {
                    prize = prize * 2;
                    this.Giai_nhi_x++;
                }

            }
     
    	
    	return prize;
    };
    Result.prototype.getPrize3D3D_GiaiBa = function(index,number1, number2, amout) {
    	var check1 = false, check2 = false;
    	var x = amout/10000;
        var prize = 0;
        var result = this.lstResultNumberString;
     
            for (var i = 12; i < 20; i++) {
                if (result[i] == number1 & !check1) check1 = true;
                else if (result[i] == number2) check2 = true;

            }

        if (check1 & check2) {
            if (Global.tBaoType < 3 && Global.tBaoType != -2) {
                this.txtTickets[index][0].addColor('#da2888', 0);
                this.txtTickets[index][1].addColor('#da2888', 0);
            }
                prize = 4000000 * x;
                //this.trung_giai += "giải tư, ";
                this.Giai_ba_x++;

                if (number1 == number2) {
                    prize = prize * 2;
                    this.Giai_ba_x++;
                }
            }
    
    	return prize;
    };
    Result.prototype.getPrize3D3D_GiaiTu = function(index,number1, number2, amout) {
    	var check1 = false, check2 = false;
    	var prize = 0;
        var x = amout / 10000;
        var result = this.lstResultNumberString;
     
            //	console.log("func giai 5 item: number1 "+ number1 + ", number1:"+ number2+", amout: "+ amout +", index: "+ index);
            for (var i = 0; i < 20; i++) {
                if (result[i] == number1 & !check1)
                    check1 = true;
                else if (result[i] == number2)
                    check2 = true;

        }


            if (check1 & check2) {
                prize = 1000000 * x;
                if (Global.tBaoType < 3 && Global.tBaoType != -2) {
                    this.txtTickets[index][0].addColor('#da2888', 0);
                    this.txtTickets[index][1].addColor('#da2888', 0);
                }
                this.Giai_tu_x++;

                if (number1 == number2) {
                    prize = prize * 2;
                    this.Giai_tu_x++;
                }
            }
    	return prize;
    };
    
    Result.prototype.getPrize3D3D_GiaiNam = function(index,number1, number2, amout) {
    	var prize = 0;
    	var Giai_nhat_1 = this.lstResultNumberString[0];
    	var Giai_nhat_2 = this.lstResultNumberString[1];
        var x = amout / 10000;
            if (Giai_nhat_1 == number1) {

                prize += 100000 * x;
                if (Global.tBaoType < 3 && Global.tBaoType != -2) {
                    this.txtTickets[index][0].addColor('#da2888', 0);
                }
                this.Giai_nam_x++;


            }
            if (Giai_nhat_1 == number2) {
                this.Giai_nam_x++;
                prize += 100000 * x;
                if (Global.tBaoType < 3 && Global.tBaoType != -2)
                this.txtTickets[index][1].addColor('#da2888', 0);
            }


        if (Giai_nhat_2 == number1) {
            if (Global.tBaoType < 3) 
                this.txtTickets[index][0].addColor('#da2888', 0);

                prize += 100000 * x;
            this.Giai_nam_x++;
            }

        if (Giai_nhat_2 == number2) {
            if (Global.tBaoType < 3 && Global.tBaoType != -2) 
                this.txtTickets[index][1].addColor('#da2888', 0);

                prize += 100000 * x;
            this.Giai_nam_x++;
            }
            if (number1 == number2 & prize != 0) {
                prize = prize * 2;
                this.Giai_nam_x = this.Giai_nam_x * 2;
            }
     
    	return prize;
    	
    };
    Result.prototype.getPrize3D3D_GiaiSau = function(index,number1, number2, amout) {
    	var prize = 0;
        var x = amout / 10000;
            for (var i = 2; i < 20; i++) {
                //console.log("giai bay "+ this.lstResultNumberString[i] +", number1: "+ number1 + ", number2: "+ number2);
                if (this.lstResultNumberString[i] == number1) {
                    prize += 40000 * x;
                    if (Global.tBaoType < 3 && Global.tBaoType != -2) 
                        this.txtTickets[index][0].addColor('#da2888', 0);

                    this.Giai_sau_x++;
                }

                if (this.lstResultNumberString[i] == number2) {
                    prize += 40000 * x;
                    if (Global.tBaoType < 3 && Global.tBaoType != -2) 
                        this.txtTickets[index][1].addColor('#da2888', 0);
                    this.Giai_sau_x++;

                }
            }

            if (number1 == number2 & prize != 0) {
                prize = prize * 2;
                this.Giai_sau_x = this.Giai_sau_x * 2;
            }

     
    	return prize;
    };
    
    Result.prototype.getPrize3D = function (type, amout) {
    	var total = 0;
    	
    	var x = amout/10000;
    	switch(type) {
    	case 1: //giai nhat
    		total = 1000000 * x;
    		this.Giai_nhat_x++;
    		break;
    	case 2: //giai nhi
    		total = 350000 * x;
    		this.Giai_nhi_x++;
    		break;
    	case 3: //gia ba
    		total = 210000 * x;
    		this.Giai_ba_x++;
    		break;
    	case 4: //giai kk
    		total = 100000 * x;
    		this.Giai_tu_x++;
    		break;
    	}
    	return total;
    };
    

    Result.prototype.numberWithCommas = function (x) {
        return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    };
  

    Result.prototype.generateRandomNumber = function (length) {
        var temp = [];
        while (true) {
            if (temp.length >= length)
                break;
            var rand = Math.random();
            var newNumber = Math.floor(rand * 10) + 0;
            temp.push(newNumber);
        }
        return temp;
    };
    Result.prototype.shuffle = function (array) {
        var currentIndex = array.length, temporaryValue, randomIndex;
        // While there remain elements to shuffle...
        while (0 !== currentIndex) {
            // Pick a remaining element...
            randomIndex = Math.floor(Math.random() * currentIndex);
            currentIndex -= 1;
            // And swap it with the current element.
            temporaryValue = array[currentIndex];
            array[currentIndex] = array[randomIndex];
            array[randomIndex] = temporaryValue;
        }
        return array;
    };
    Result.prototype.setDrag = function (obj) {
        obj.inputEnabled = true;
        obj.input.enableDrag(true);
        obj.events.onInputUp.add(function () {
            console.log(obj.x + '|' + obj.y);
        }, this);
    };
    return Result;
}());
//# sourceMappingURL=result.js.map

String.prototype.replaceAll = function (find, replace) {
    var str = this;
    return str.replace(new RegExp(find, 'g'), replace);
};

function permutator(inputArr) {
    var results = [];

    function permute(arr, memo) {
        var cur, memo = memo || [];

        for (var i = 0; i < arr.length; i++) {
            cur = arr.splice(i, 1);
            if (arr.length === 0) {
                results.push(memo.concat(cur));
            }
            permute(arr.slice(), memo.concat(cur));
            arr.splice(i, 0, cur[0]);
        }

        return results;
    }
    let array = permute(inputArr);
    let _return = [];
    for (var i = 0; i < array.length; i++) {
        _return.push(array[i].join().replaceAll(',', ''));
    }


    return removeDuplicates(_return);
}

function removeDuplicates(data) {
    return data.filter((value, index) => data.indexOf(value) === index);
}

