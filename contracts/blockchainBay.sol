// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

contract BlockchainBay { 

    // Total text links
    uint256 public asciiCount;
    // Mapping from Item Ids to Item data in Ascii (unoptimized). 
    mapping(uint256=>string) public ItemsAscii;

    // Optimized Magnet link
    bytes32[10][] Magnet;

    struct TMagnet { bytes32[10] slice; }
    
     // Contract version
     function version() public view returns (uint) {
      return 0x0100;
     }
      //-------------ASCII link functions-----------------
      //This allows to store any unformatted link
    
      // Create a link in ascii form (unlimited lenght).
     function createAscii(string memory data) public returns (uint) {
        require(bytes(data).length>10, "Torrent description too short");
         ItemsAscii[asciiCount] = data;
	      asciiCount++;
	     return (asciiCount-1);
	}

     // Retrieve single link
     function getAscii(uint256 Id) public view returns(string memory) {
        return ItemsAscii[Id];
     }

     //Retrieve range of items
     function getAsciiMulti(uint256 minId, uint256 maxId) public view returns(string[] memory) {
        string[] memory lItems = new string[](maxId-minId);
        for (uint i=minId;i<maxId;i++) {
           lItems[i-minId]=ItemsAscii[i];
	   }
        return lItems;
     }

   
      //-------------Magnet link functions-----------------
      // This allows to store magnets uising bytes32
      // Chaper and faster than ascii links

   // Returns amount of links
   function getMagnetCount() public view returns (uint256) {
      return Magnet.length;
   }

   // Create a single magnet link
   function createMagnet(bytes32[] memory data) public returns (uint256) {
        bytes32[10] memory test;
        for(uint i=0;i<data.length;i++)
         test[i]=data[i];
        Magnet.push(test);
	     return (Magnet.length-1);
	}

   // Create multiple magnet links
   function createMagnet10(bytes32[][10] memory data) public returns (uint256) {
        bytes32[10] memory test;
        for(uint q=0;q<10;q++) {
         for(uint i=0;i<10;i++)
            if (i<data[q].length)
               test[i]=data[q][i];
            else 
               test[i]=0;
         Magnet.push(test);
        }
	     return (Magnet.length-1);
	}

   // Retrieve a magnet given their index
     function getMagnet(uint256 Id) public view returns(bytes32[10] memory) {
        return Magnet[Id];
     }


   // Retrieve multiple magnets given a range
     function getMagnets(uint256 minId, uint256 maxId) public view returns(TMagnet[] memory) {
        TMagnet[] memory lItems = new TMagnet[](maxId-minId);
        for (uint i=minId;i<maxId;i++) {
           lItems[i-minId].slice=Magnet[i];
	   }
        return lItems;

     }
    
     // Vote function: Increments the LSB of the data (second) array of the magnet entry
     // Doesn't operate on ascii links
     function vote(uint256 Id) public {
      bytes32 mask=bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00);
      uint8 b=uint8(Magnet[Id][1][0]);
      if (b<0xff) {
         b++;
         Magnet[Id][1] =  ( Magnet[Id][1] & mask) | bytes1(b);
      }
     }

   // Search a magnet given a Id range and a subtext. Return array of matches.
   // Warning: This function might be slow.
   function searchMagnet(uint256 minId,uint256 maxId, bytes memory what) public view returns(uint256 Count,TMagnet[20] memory) {
    uint256 foundCount;
    TMagnet[20] memory foundMagnets;
    for (uint q = minId; q< maxId; q++) {
     for (uint i = 0; i <= 256 - what.length; i++) {
        bool flag = true;
        bytes1 b;
        for (uint j = 0; j < what.length; j++) {
            uint256 index1=(i+j) % 32; // Index inside the word
            uint256 index2=(i+j) / 32; // Word index
            b =Magnet[q][index2+2][index1];
            if ((b==0) || (b != what[j])) {
                flag = false;
                break;
               }
            }
        if (b==0) break; // reached end of title, continue to the next
        if (flag) {
            foundMagnets[foundCount++].slice=Magnet[q];
            if(foundCount>=20)
               return(foundCount,foundMagnets);
            break;
            }
         }
      }
    return (foundCount,foundMagnets);
   }
   
}

