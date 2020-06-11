with Ada.Text_IO;
with Ada.Strings.Fixed;
use Ada.Text_IO;

procedure Main is
begin
  Put_Line (Ada.Strings.Fixed.Trim (Integer'Image (2 * (Integer'Value (Get_Line))), Ada.Strings.Left));
end;
