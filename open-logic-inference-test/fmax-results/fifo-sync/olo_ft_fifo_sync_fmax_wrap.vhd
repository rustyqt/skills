---------------------------------------------------------------------------------------------------
-- TEMPORARY Fmax measurement harness for olo_ft_fifo_sync - NOT for commit.
-- Places an olo_base_pl_stage on the input and on the output side of the FIFO so that the
-- combinational ECC encode and decode paths are timed as register-to-register paths.
---------------------------------------------------------------------------------------------------
library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;

library work;
    use work.olo_base_pkg_math.all;
    use work.olo_ft_pkg_ecc.all;

entity olo_ft_fifo_sync_fmax_wrap is
    generic (
        Width_g       : positive             := 32;
        Depth_g       : positive             := 256;
        EccPipeline_g : natural range 0 to 2 := 0
    );
    port (
        Clk               : in    std_logic;
        Rst               : in    std_logic;
        In_Data           : in    std_logic_vector(Width_g - 1 downto 0);
        In_Valid          : in    std_logic;
        In_Ready          : out   std_logic;
        In_Level          : out   std_logic_vector(log2ceil(Depth_g + 1) - 1 downto 0);
        Out_Data          : out   std_logic_vector(Width_g - 1 downto 0);
        Out_Valid         : out   std_logic;
        Out_Ready         : in    std_logic;
        Out_Level         : out   std_logic_vector(log2ceil(Depth_g + 1) - 1 downto 0);
        Out_EccSec        : out   std_logic;
        Out_EccDed        : out   std_logic;
        Full              : out   std_logic;
        AlmFull           : out   std_logic;
        Empty             : out   std_logic;
        AlmEmpty          : out   std_logic;
        In_ErrInj_BitFlip : in    std_logic_vector(eccCodewordWidth(Width_g) - 1 downto 0);
        In_ErrInj_Valid   : in    std_logic
    );
end entity;

architecture rtl of olo_ft_fifo_sync_fmax_wrap is

    -- Output pipeline stage carries the ECC flags alongside the data
    constant BundleWidth_c : positive := Width_g + 2;

    signal PlIn_Data  : std_logic_vector(Width_g - 1 downto 0);
    signal PlIn_Valid : std_logic;
    signal PlIn_Ready : std_logic;

    signal FifoOut_Data  : std_logic_vector(Width_g - 1 downto 0);
    signal FifoOut_Valid : std_logic;
    signal FifoOut_Ready : std_logic;
    signal FifoOut_Sec   : std_logic;
    signal FifoOut_Ded   : std_logic;

    signal PlOut_InData  : std_logic_vector(BundleWidth_c - 1 downto 0);
    signal PlOut_OutData : std_logic_vector(BundleWidth_c - 1 downto 0);

begin

    i_pl_in : entity work.olo_base_pl_stage
        generic map (
            Width_g    => Width_g,
            UseReady_g => true,
            Stages_g   => 1
        )
        port map (
            Clk       => Clk,
            Rst       => Rst,
            In_Valid  => In_Valid,
            In_Ready  => In_Ready,
            In_Data   => In_Data,
            Out_Valid => PlIn_Valid,
            Out_Ready => PlIn_Ready,
            Out_Data  => PlIn_Data
        );

    i_fifo : entity work.olo_ft_fifo_sync
        generic map (
            Width_g         => Width_g,
            Depth_g         => Depth_g,
            AlmFullOn_g     => true,
            AlmFullLevel_g  => Depth_g - 4,
            AlmEmptyOn_g    => true,
            AlmEmptyLevel_g => 4,
            EccPipeline_g   => EccPipeline_g
        )
        port map (
            Clk               => Clk,
            Rst               => Rst,
            In_Data           => PlIn_Data,
            In_Valid          => PlIn_Valid,
            In_Ready          => PlIn_Ready,
            In_Level          => In_Level,
            Out_Data          => FifoOut_Data,
            Out_Valid         => FifoOut_Valid,
            Out_Ready         => FifoOut_Ready,
            Out_Level         => Out_Level,
            Out_EccSec        => FifoOut_Sec,
            Out_EccDed        => FifoOut_Ded,
            Full              => Full,
            AlmFull           => AlmFull,
            Empty             => Empty,
            AlmEmpty          => AlmEmpty,
            In_ErrInj_BitFlip => In_ErrInj_BitFlip,
            In_ErrInj_Valid   => In_ErrInj_Valid
        );

    PlOut_InData <= FifoOut_Sec & FifoOut_Ded & FifoOut_Data;

    i_pl_out : entity work.olo_base_pl_stage
        generic map (
            Width_g    => BundleWidth_c,
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
    Out_EccDed <= PlOut_OutData(Width_g);
    Out_EccSec <= PlOut_OutData(Width_g + 1);

end architecture;
