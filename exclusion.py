REAL_ESTATE = ['ALSC3', 'ALSO3', 'BBRK3', 'BRML3', 'BRPR3', 'CALI3', 'CCPR3', 'CORR4', 'CRDE3', 
               'CURY3', 'CYRE3', 'DIRR3', 'EVEN3', 'EZTC3', 'GFSA3', 'GSHP3', 'HBOR3', 'HBOR3', 
               'IGBR3', 'IGTA3', 'INNT3', 'JFEN3', 'JHSF3', 'JPSA3', 'JPSA4', 'LAVV3', 'LAVV3', 
               'LOGG3', 'LPSB3', 'MDNE3', 'MDNE3', 'MELK3', 'MLFT3', 'MLFT4', 'MRVE3', 'MTRE3', 
               'MTRE3', 'MULT3', 'PDGR3', 'PLPL3', 'RDNI3', 'RSID3', 'SCAR3', 'SSBR3', 'TEND3',
               'TCSA3', 'TRIS3', 'VIVR3']

FINANCIALS = ['ABCB4', 'APER3', 'B3SA3', 'BAHI3', 'BAHI4', 'BAZA3', 'BBAS3', 'BBDC3', 'BBDC4', 
              'BBSE3', 'BBTG11', 'BBTG12', 'BEES3', 'BEES4', 'BGIP3', 'BGIP4', 'BICB3', 'BICB4', 
              'BIDI11', 'BIDI3', 'BIDI4', 'BMEB3', 'BMEB4', 'BMGB11', 'BMGB4', 'BMIN3', 'BMIN4', 
              'BNBR3', 'BNBR4', 'BPAC11', 'BPAC13', 'BPAC3', 'BPAC5', 'BPAN4', 'BPAT11', 'BPNM4', 
              'BRGE11', 'BRGE12', 'BRGE3', 'BRGE5', 'BRGE6', 'BRGE7', 'BRGE8', 'BRIN3', 'BRIV3', 
              'BRIV4', 'BRSR3', 'BRSR5', 'BRSR6', 'BSAN33', 'BSLI3', 'BSLI4', 'BVMF3', 'CRIV3', 
              'CRIV4', 'CSAB3', 'CSAB4', 'CTIP3', 'DAYC4', 'FIGE3', 'FIGE4', 'GPIV11', 'GPIV33', 
              'IDNT3', 'IDVL3', 'IDVL4', 'IRBR3', 'ITAU3', 'ITAU4', 'ITSA3', 'ITSA4', 'ITUB3', 
              'ITUB4', 'MAPT3', 'MAPT4', 'MERC3', 'MERC4', 'MOAR3', 'PARC3', 'PDTC3', 'PINE4', 
              'PPLA11', 'PRBC4', 'PSSA3', 'RJCP3', 'RPAD3', 'RPAD5', 'RPAD6', 'SANB11', 'SANB3', 
              'SANB4', 'SFSA4', 'SULA11', 'SULA3', 'SULA4', 'TRPN3', 'WIZS3']

EXCEPTIONS = [
    'ECOD3',
    'CESP3', 'CESP4', 'CESP5', 'CESP6', # nao possui balanco consolidado (calcular sobre individual)
    ]

EXCLUDED = REAL_ESTATE + FINANCIALS + EXCEPTIONS