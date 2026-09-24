---------------------------------------------------------------------------------------------------
-- TEMPORARY Fmax measurement harness for olo_ft_fifo_packet - NOT for commit.
-- Places an olo_base_pl_stage on the input and on the output side of the FIFO so that the
-- combinational ECC encode and decode paths are timed as register-to-register paths. The
-- per-beat sidebands travel through the pipeline stages together with the data.
---------------------------------------------------------------------------------------------------
library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;

library work;
    use work.olo_base_pkg_math.all;
    use work.olo_ft_pkg_ecc.all;

entity olo_ft_fifo_packet_fmax_wrap is
    generic (
        Width_g       : positive                            := 32;
        Depth_g       : positive                            := 256;
        MaxPackets_g  : positive range 2 to positive'high    := 17;
        EccPipeline_g : natural range 0 to 2                 := 0
    );
    port (
        Clk               : in    std_logic;
        Rst               : in    std_logic;
        In_Data           : in    std_logic_vector(Width_g - 1 downto 0);
        In_Valid          : in    std_logic;
        In_Ready          : out   std_logic;
        In_Last           : in    std_logic;
        In_Drop           : in    std_logic;
        In_IsDropped      : out   std_logic;
        Out_Data          : out   std_logic_vector(Width_g - 1 downto 0);
        Out_Valid         : out   std_logic;
        Out_Ready         : in    std_logic;
        Out_Size          : out   std_logic_vector(log2ceil(Depth_g + 1) - 1 downto 0);
        Out_Last          : out   std_logic;
        Out_Next          : in    std_logic;
        Out_Repeat        : in    std_logic;
        Out_EccSec        : out   std_logic;
        Out_EccDed        : out   std_logic;
        PacketLevel       : out   std_logic_vector(log2ceil(MaxPackets_g + 1) - 1 downto 0);
        FreeWords         : out   std_logic_vector(log2ceil(Depth_g + 1) - 1 downto 0);
        In_ErrInj_BitFlip : in    std_logic_vector(eccCodewordWidth(Width_g) - 1 downto 0);
        In_ErrInj_Valid   : in    std_logic
    );
end entity;

architecture rtl of olo_ft_fifo_packet_fmax_wrap is

    constant SizeWidth_c   : positive := log2ceil(Depth_g + 1);
    -- Input stage carries {Drop, Last, Data}
    constant InBundle_c    : positive := Width_g + 2;
    -- Output stage carries {EccSec, EccDed, Last, Size, Data}
    constant OutBundle_c   : positive := Width_g + SizeWidth_c + 3;

    signal PlIn_InData  : std_logic_vector(InBundle_c - 1 downto 0);
    signal PlIn_OutData : std_logic_vector(InBundle_c - 1 downto 0);
    signal PlIn_Valid   : std_logic;
    signal PlIn_Ready   : std_logic;

    signal FifoOut_Data  : std_logic_vector(Width_g - 1 downto 0);
    signal FifoOut_Valid : std_logic;
    signal FifoOut_Ready : std_logic;
    signal FifoOut_Size  : std_logic_vector(SizeWidth_c - 1 downto 0);
    signal FifoOut_Last  : std_logic;
    signal FifoOut_Sec   : std_logic;
    signal FifoOut_Ded   : std_logic;

    signal PlOut_InData  : std_logic_vector(OutBundle_c - 1 downto 0);
    signal PlOut_OutData : std_logic_vector(OutBundle_c - 1 downto 0);

begin

    PlIn_InData <= In_Drop & In_Last & In_Data;

    i_pl_in : entity work.olo_base_pl_stage
        generic map (
            Width_g    => InBundle_c,
            UseReady_g => true,
            Stages_g   => 1
        )
        port map (
            Clk       => Clk,
            Rst       => Rst,
            In_Valid  => In_Valid,
            In_Ready  => In_Ready,
            In_Data   => PlIn_InData,
            Out_Valid => PlIn_Valid,
            Out_Ready => PlIn_Ready,
            Out_Data  => PlIn_OutData
        );

    i_fifo : entity work.olo_ft_fifo_packet
        generic map (
            Width_g       => Width_g,
            Depth_g       => Depth_g,
            MaxPackets_g  => MaxPackets_g,
            EccPipeline_g => EccPipeline_g
        )
        port map (
            Clk               => Clk,
            Rst               => Rst,
            In_Valid          => PlIn_Valid,
            In_Ready          => PlIn_Ready,
            In_Data           => PlIn_OutData(Width_g - 1 downto 0),
            In_Last           => PlIn_OutData(Width_g),
            In_Drop           => PlIn_OutData(Width_g + 1),
            In_IsDropped      => In_IsDropped,
            Out_Valid         => FifoOut_Valid,
            Out_Ready         => FifoOut_Ready,
            Out_Data          => FifoOut_Data,
            Out_Size          => FifoOut_Size,
            Out_Last          => FifoOut_Last,
            Out_Next          => Out_Next,
            Out_Repeat        => Out_Repeat,
            Out_EccSec        => FifoOut_Sec,
            Out_EccDed        => FifoOut_Ded,
            PacketLevel       => PacketLevel,
            FreeWords         => FreeWords,
            In_ErrInj_BitFlip => In_ErrInj_BitFlip,
            In_ErrInj_Valid   => In_ErrInj_Valid
        );

    PlOut_InData <= FifoOut_Sec & FifoOut_Ded & FifoOut_Last & FifoOut_Size & FifoOut_Data;

    i_pl_out : entity work.olo_base_pl_stage
        generic map (
            Width_g    => OutBundle_c,
            UseReady_g => true,
            Stages_g   => 1
        )
        port map (
            Clk       => Clk,
            Rst       => Rst,
            In_Valid  => FifoOut_Valid,
            In_Ready  => FifoOut_Ready,
            In_Data   => PlOut_InData,
            Out_Valid => Out_Valid,
            Out_Ready => Out_Ready,
            Out_Data  => PlOut_OutData
        );

    Out_Data   <= PlOut_OutData(Width_g - 1 downto 0);
    Out_Size   <= PlOut_OutData(Width_g + SizeWidth_c - 1 downto Width_g);
    Out_Last   <= PlOut_OutData(Width_g + SizeWidth_c);
    Out_EccDed <= PlOut_OutData(Width_g + SizeWidth_c + 1);
    Out_EccSec <= PlOut_OutData(Width_g + SizeWidth_c + 2);

end architecture;
